import logging
import socket
import re
import gevent
from StringIO import StringIO
from six.moves import urllib_parse as urlparse

from cachebrowser.models import Host
from cachebrowser.network import ConnectionHandler
from cachebrowser.common import silent_fail
from cachebrowser import http
from cachebrowser import dns


class ProxyConnection(ConnectionHandler):
    def __init__(self, *args, **kwargs):
        super(ProxyConnection, self).__init__(*args, **kwargs)
        self._buffer = StringIO()
        self._schema = None

        self._local_socket = None
        self._remote_socket = None

        self.on_data = self.on_local_data
        self.on_close = self.on_local_closed

    def on_data(self, data):
        self.on_local_data(data)

    def on_connect(self, sock, address):
        self._local_socket = sock
        # logging.debug("New proxy connection established with %s" % str(self.address))

    @silent_fail(log=True)
    def on_local_data(self, data):
        if len(data) == 0:
            return

        if self._schema is not None:
            if hasattr(self._schema, 'on_local_data'):
                return self._schema.on_local_data(data)
        else:
            self._buffer.write(data)
            schema = self._check_for_schema()
            if schema is not None:
                self._schema = schema(self, self._buffer)

    @silent_fail(log=True)
    def on_remote_data(self, data):
        if len(data) == 0:
            return

        if hasattr(self._schema, 'on_remote_data'):
            return self._schema.on_remote_data(data)

    @silent_fail(log=True)
    def on_local_closed(self):
        if self._remote_socket is None:
            return

        try:
            self._remote_socket.close()
        except socket.error:
            pass

    @silent_fail(log=True)
    def on_remote_closed(self):
        try:
            self._local_socket.close()
        except socket.error:
            pass

    def start_remote(self, sock):
        self._remote_socket = sock

        def remote_reader():
            try:
                while True:
                    buff = sock.recv(1024)
                    gevent.sleep(0)
                    if not buff:
                        self.on_remote_closed()
                        break

                    self.on_remote_data(buff)
            except Exception as e:
                logging.error(e)
        gevent.spawn(remote_reader)

    def send_remote(self, data):
        if len(data) == 0:
            return
        self._remote_socket.send(data)

    def send_local(self, data):
        if len(data) == 0:
            return
        self._local_socket.send(data)

    def close_local(self):
        self._local_socket.close()

    def close_remote(self):
        self._remote_socket.close()

    def _check_for_schema(self):
        buff = self._buffer.getvalue()
        if '\n' in buff:
            self._buffer.seek(0)
            firstline = self._buffer.readline()
            match = re.match("(?:GET|POST|PUT|DELETE|HEAD) (.+) \w+", firstline)
            if match is not None:
                return HttpSchema
            match = re.match("(?:CONNECT) (.+) \w*", firstline)
            if match is not None:
                return SSLSchema
        return None


class HttpSchema(object):
    def __init__(self, connection, buff=None):
        self._connection = connection
        self._upstream_started = False
        self.request_builder = http.HttpRequest.Builder()
        self.cachebrowsed = False

        if buff is not None:
            self.on_local_data(buff.getvalue())

    def on_local_data(self, data):
        if not self._upstream_started:
            self.request_builder.write(data)
            self._check_request()

    def on_remote_data(self, data):
        if self.cachebrowsed and 'Location: ' in data:
            data = data.replace('Location: https', 'Location: http')

        self._connection.send_local(data)

    def _check_request(self):
        if not self.request_builder.is_ready():
            return
        self._upstream_started = True
        self._start_remote()

    def _start_remote(self):
        http_request = self.request_builder.http_request

        url = http_request.path
        parsed_url = urlparse.urlparse(url)
        try:
            host = Host.get(Host.hostname==parsed_url.hostname)
            if host.ssl:
                url = url.replace('http', 'https')
            self.cachebrowsed = True
        except Host.DoesNotExist:
            pass

        logging.info("[%s] %s %s" % (http_request.method, url, '<CACHEBROWSED>' if self.cachebrowsed else ''))
        request = http_request.get_raw()
        # request = re.sub(r'^(GET|POST|PUT|DELETE|HEAD) http[s]?://[^/]+/(.+) (\w+)', r'\1 /\2 \3', request)
        response = http.request(url, raw_request=request)

        self._connection.start_remote(response)


class SSLSchema(object):
    def __init__(self, connection, buff=None):
        self.connection = connection
        self._buffer = buff or StringIO()
        self._upstream_started = False
        self._host = None
        self._start_upstream()
        # connection.close_local()

        self.connection = connection

    def on_local_data(self, data):
        if not self._upstream_started and not self._start_upstream():
            self._buffer.seek(0, 2)
            self._buffer.write(data)
            return
        else:
            self.connection.send_remote(data)

    def on_remote_data(self, data):
        self.connection.send_local(data)

    def _start_upstream(self):
        self._buffer.seek(0)
        firstline = self._buffer.readline()
        match = re.match("(?:CONNECT) ([^:]+)(?:[:](\d+))? \w+", firstline)
        if match is None:
            return

        host = match.group(1)
        port = int(match.group(2) or 443)

        cachebrowsed = False
        try:
            Host.get(Host.hostname == host)
            cachebrowsed = True
        except Host.DoesNotExist:
            pass

        if cachebrowsed:
            logging.info("[HTTPS] %s:%s  <REJECTED>" % (host, port))
            self.connection.close_local()
        else:
            logging.info("[HTTPS] %s:%s  <PROXYING>" % (host, port))
            return self._connect_upstream(host, port)

    def _connect_upstream(self, host, port):
        ip, cachebrowsed = dns.resolve_host(host)
        if not ip:
            return

        # Return response to client
        self.connection.send_local("HTTP/1.1 200 OK\r\n\r\n")

        # Create remote socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Shouldn't use SSL, ssl is forwarded directly from the client
        # sock = ssl.wrap_socket(sock)
        sock.connect((ip, port))

        self._upstream_started = True
        self._host = host

        # ! Ref to connection._buffer not updated
        self._buffer = StringIO()

        # !! Why does this line not work here?
        # self.connection.send_local("HTTP/1.1 200 OK\r\n\r\n")

        self.connection.start_remote(sock)

        return True
