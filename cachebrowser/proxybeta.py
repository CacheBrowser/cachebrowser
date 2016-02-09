import re

import errno
import requests
import json
import sys

import socket

from cachebrowser import dns
from cachebrowser.common import silent_fail, logger
from cachebrowser.network import HttpConnectionHandler, gevent, ConnectionHandler

count = 0

class ProxyHandler(HttpConnectionHandler):
    def on_request(self, env, start_response):
        method = env['REQUEST_METHOD']

        if method == 'CONNECT':
            return self.proxy_https(env, start_response)
        else:
            return self.proxy_http(env, start_response)

    def proxy_http(self, env, start_response):
        headers = self.extract_http_headers(env)
        body = self.extract_http_body(env)

        url = env['PATH_INFO']
        match = re.match('http://([^/?]+)(?:.+)?', url)
        host = match.group(1)
        ip, cachebrowsed = dns.resolve_host(host)
        changed_url = url.replace(host, ip, 1)

        # TODO Remove PROXY_CONNECTION header
        options = {
            'method': env['REQUEST_METHOD'],
            'url': changed_url,
            'headers': headers,
        }

        if env['QUERY_STRING']:
            options['params'] = env['QUERY_STRING']

        if body:
            options['data'] = body

        session = requests.Session()
        request = requests.Request(**options)
        prepared_request = request.prepare()
        response = session.send(prepared_request, stream=True, allow_redirects=False)

        proxy_logger.log(host, 80, ip, 'http', cachebrowsed=cachebrowsed, url=url)

        start_response("%d %s" % (response.status_code, response.reason), list(response.headers.iteritems()))

        if response.headers.get('Transfer-Encoding', None) == 'chunked':
            return response.raw
        return response.raw.data

    def extract_http_headers(self, env):
        headers = {}
        for key in env:
            if key.startswith('HTTP_'):
                headers[key.replace('HTTP_', '').title()] = env[key]
        return headers

    def extract_http_body(self, env):
        return env['wsgi.input'].read()


class SSLProxyHandler(ConnectionHandler):
    def __init__(self, *args, **kwargs):
        super(SSLProxyHandler, self).__init__(*args, **kwargs)
        self._local_socket = None
        self._remote_socket = None

        self.remote_connection_established = False

        self.on_data = self.on_local_data
        self.on_close = self.on_local_closed

    def on_connect(self, sock, address):
        self._local_socket = sock
        # logger.debug("New proxy connection established with %s" % str(self.address))

    # @silent_fail(log=True)
    def on_local_data(self, data):
        # print("LOCAL DATA %d" % len(data))
        # print(data)
        if len(data) == 0:
            return

        if not self.remote_connection_established:
            match = re.match("(?:CONNECT) ([^:]+)(?:[:](\d+))? \w+", data)
            host = match.group(1)
            port = int(match.group(2) or 443)

            ip, cachebrowsed = dns.resolve_host(host)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, port))
            self.remote_connection_established = True
            self.start_remote(sock)

            self.send_local("HTTP/1.1 200 OK\r\n\r\n")

            proxy_logger.log(host, port, ip, 'https')
        else:
            self.send_remote(data)

    # @silent_fail(log=True)
    def on_remote_data(self, data):
        # print("REMOTE DATA %d" % len(data))
        # print(data)
        if len(data) == 0:
            return

        self.send_local(data)

    # @silent_fail(log=True)
    def on_local_closed(self):
        print("LOCAL CLOSED")
        if self._remote_socket is None:
            return

        try:
            self._remote_socket.close()
        except socket.error:
            pass

    # @silent_fail(log=True)
    def on_remote_closed(self):
        print("REMOTE CLOSED")
        try:
            self._local_socket.close()
        except socket.error:
            pass

    def start_remote(self, sock):
        global count
        print("START REMOTE")
        self._remote_socket = sock

        def remote_reader():
            global count
            count += 1
            print(">>>>>>>>>>>>> GOING UP %d" % count)
            try:
                while True:
                    buff = sock.recv(1024)
                    gevent.sleep(0)
                    if not buff:
                        self.on_remote_closed()
                        break

                    self.on_remote_data(buff)
            except socket.error as e:
                if e.errno != errno.EBADF:
                    logger.error(e)
                    #   TODO REMOVE
                    raise
            except Exception as e:
                logger.error(e)
                #   TODO REMOVE
                raise
            count -= 1
            print(">>>>>>>>>>>>> GOING DOWN %d" % count)


        gevent.spawn(remote_reader)


    def send_remote(self, data):
        # print("SEND REMOTE %d" % len(data))
        if len(data) == 0:
            return

        self._remote_socket.send(data)

    def send_local(self, data):
        # print("SEND LOCAL %d" % len(data))
        if len(data) == 0:
            return

        self._local_socket.send(data)

    def close_local(self):
        print("CLOSE LOCAL")
        self._local_socket.close()

    def close_remote(self):
        print("CLOSE REMOTE")
        self._remote_socket.close()


class ProxyLogger(object):
    def __init__(self):
        self.handlers = []

    def log(self, host, port, target, scheme, url=None, cachebrowsed=False):
        for handler in self.handlers:
            handler(host=host, port=port, target=target, scheme=scheme, url=url, cachebrowsed=cachebrowsed)

    def register_handler(self, handler):
        self.handlers.append(handler)

    def remove_handler(self, handler):
        self.handlers.remove(handler)

proxy_logger = ProxyLogger()