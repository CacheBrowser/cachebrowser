import os
import socket
import threading
from cachebrowser import dns
import httplib
import logging
import re
import ssl
import urlparse
import StringIO
from cachebrowser.common import silent_fail
from cachebrowser.eventloop import looper


def request(url, method='GET', target=None, headers=None, port=None, scheme='http', callback=None):
    if not headers: headers = {}
    if '://' not in url:
        url = scheme + '://' + url
    parsed_url = urlparse.urlparse(url, scheme=scheme)

    if target:
        target, cachebrowsed = dns.resolve_host(target, use_cachebrowser_db=False)
    else:
        target, cachebrowsed = dns.resolve_host(parsed_url.hostname)

    # if not cachebrowsed:
    # target = parsed_url.hostname

    headers = headers or {}
    for header in headers.keys():
        if ':' in header:
            del headers[header]
    headers["Host"] = parsed_url.hostname
    if "Connection" not in headers or True:
        headers["Connection"] = "Close"

    http_request = HttpRequest()
    http_request.method = method
    http_request.path = parsed_url.path or '/'
    http_request.headers = headers

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if parsed_url.scheme == 'https':
        sock = ssl.wrap_socket(sock)
    sock.connect((target, port or (443 if parsed_url.scheme == 'https' else 80)))

    response_builder = HttpResponse.Builder()

    def on_data(data):
        response_builder.write(data)

    def on_close():
        http_response = response_builder.http_response
        if callback is not None:
            callback(http_response)

    # TODO not working don't know why
    # looper.register_socket(sock, on_data, on_close)

    sock.send(http_request.get_raw())

    def recv():
        while 1:
            buf = sock.recv(1024)
            on_data(buf)
            if not len(buf):
                on_close()
                break

    threading.Thread(target=recv).start()


def handle_connection(conn, addr, looper):
    handler = HttpHandler(conn)
    # logging.debug("New HTTP connection established with %s" % str(addr))
    looper.register_socket(conn, handler.on_data, handler.on_close)


class HttpHandler(object):
    def __init__(self, sock):
        self._buffer = StringIO.StringIO()
        self._socket = sock
        self.url = None
        self.headers = {}

    @silent_fail(log=True)
    def on_data(self, data):
        try:
            self._buffer.write(data)
            all_data = self._buffer.getvalue()
            if '\r\n\r\n' in all_data:
                if self._parse_request():
                    self._send_upstream_request()
        except:
            self._socket.close()
            raise

    def on_close(self):
        pass

    def send(self, data):
        self._socket.send(data)

    def _parse_request(self):
        self._buffer.seek(0)
        request_line = self._buffer.readline()  # e.g. GET /v?v='http://www.nbc.com' HTTP/1.1

        match = re.match("(GET|POST|PUT|DELETE|HEAD) (.+) .+", request_line)
        if match is None:
            raise ValueError("Invalid HTTP request %s" % request_line)

        self.method = match.group(1)  # e.g. GET

        whole_url = match.group(2)  # e.g. /?v='http://www.nbc.com'

        parsed_whole_url = urlparse.urlparse(whole_url)
        params = urlparse.parse_qs(parsed_whole_url.query)

        url_param = params.get('v', None)  # e.g. http://www.nbc.com
        if url_param is None or len(url_param) == 0:
            logging.warning("Skipping %s" % whole_url.strip())
            return
            # raise ValueError("No request url received in HTTP request")
        self.url = url_param[0]

        for line in self._buffer.readlines():
            match = re.match("(.+):\\s*(.+)", line.strip())
            if match is None:
                continue
            self.headers[match.group(1)] = match.group(2)

        return True

    def _send_upstream_request(self):
        def on_response(response):
            raw_response = response.get_raw()
            raw_response = re.sub('((?:src|href|ng-src|ng-href)\s*=\s*)[\'"]((?:(?:http|https):/)?.*/.*)[\'"]', r'\1"http://127.0.0.1:9000/?v=\2"', raw_response)
            self.send(raw_response)
            self._socket.close()

        logging.info("%s %s" % (self.method, self.url))
        request(self.url, method=self.method, headers=self.headers, callback=on_response)


class HttpRequest(object):
    class Builder(object):
        def __init__(self):
            self._buffer = StringIO.StringIO()
            self._state = 'request'
            self._pos = 0
            self.http_request = HttpRequest()

        def write(self, data):
            self._buffer.seek(0, os.SEEK_END)
            self._buffer.write(data)
            self._parse()

        def _parse(self):
            while self._pos != self._buffer.len:
                self._buffer.seek(self._pos)

                if self._state == 'body':
                    self._buffer.seek(self._pos)
                    self.http_request.body += self._buffer.read()
                    self._pos = self._buffer.pos
                    self.http_request.raw = self._buffer.getvalue()
                    return self.http_request

                line = self._buffer.readline()
                if not line.endswith('\n'):
                    return

                self._pos = self._buffer.pos

                if self._state == 'request':
                    match = re.match("(?:GET|POST|PUT|DELETE|HEAD) (.+) \w+", line)
                    if match is None:
                        raise ValueError("Invalid request line: %s" % line)
                    self.http_request.method = match.group(1)
                    self.http_request.path = match.group(2)
                    self._state = 'headers'
                elif self._state == 'headers':
                    match = re.match("^\s*$", line)
                    if match is not None:
                        self._state = 'body'
                        self.http_request.raw = self._buffer.getvalue()
                        return self.http_request

                    match = re.match("(.+): .+", line)
                    if match is None:
                        raise ValueError("Invalid header: %s" % line)
                    self.http_request.headers[match.group(1)] = match.group(2)

    def __init__(self):
        self.method = None
        self.path = None
        self.headers = {}
        self.raw = ''
        self.body = ''

    def get_raw(self):
        if not self.raw:
            buff = StringIO.StringIO()
            buff.write('%s %s HTTP/1.1\r\n' % (self.method, self.path))

            for header in self.headers:
                buff.write('%s: %s\r\n' % (header, self.headers[header]))
            buff.write('\r\n')
            if self.body:
                buff.write(self.body)
            self.raw = buff.getvalue()
        return self.raw


class HttpResponse(object):
    class Builder(object):
        def __init__(self):
            self._buffer = StringIO.StringIO()
            self._pos = 0
            self._state = 'status'
            self.http_response = HttpResponse()

        def write(self, data):
            self._buffer.seek(0, os.SEEK_END)
            self._buffer.write(data)

            self._parse()

        def _parse(self):
            while self._pos != self._buffer.len:
                self._buffer.seek(self._pos)

                if self._state == 'body':
                    self._buffer.seek(self._pos)
                    self.http_response.body += self._buffer.read()
                    self._pos = self._buffer.pos
                    self.http_response.raw = self._buffer.getvalue()
                    return self.http_response

                line = self._buffer.readline()
                if not line.endswith('\n'):
                    return

                self._pos = self._buffer.pos

                if self._state == 'status':
                    match = re.match('.+ (\d+) (.+)', line)
                    if match is None:
                        raise ValueError("Invalid Http Response status line: %s" % line)
                    self.http_response.status = int(match.group(1))
                    self.http_response.reason = match.group(2)
                    self._state = 'headers'

                elif self._state == 'headers':
                    match = re.match("^\s*$", line)
                    if match is not None:
                        self._state = 'body'
                        self.http_response.raw = self._buffer.getvalue()
                        return self.http_response

                    match = re.match("(.+): (.+)", line)
                    if match is None:
                        raise ValueError("Invalid header: %s" % line)
                    self.http_response.headers[match.group(1)] = match.group(2)

    def __init__(self):
        self.status = None
        self.reason = None
        self.body = ''
        self.headers = {}
        self.raw = ''

    def get_raw(self):
        if not self.raw:
            buff = StringIO.StringIO()
            buff.write('HTTP/1.1 %d %s\r\n' % (self.status, self.reason))

            for header in self.headers:
                buff.write('%s: %s\r\n' % (header, self.headers[header]))
            buff.write('\r\n')
            if self.body:
                buff.write(self.body)
            self.raw = buff.getvalue()
        return self.raw

