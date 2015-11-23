import os
import socket
import httplib
import logging
import re
import ssl
import urlparse
import StringIO

from cachebrowser.common import silent_fail
from cachebrowser import dns


def request(url, method=None, target=None, cachebrowse=None, headers=None, port=None, scheme='http', raw_request=None):
    if raw_request is not None and (headers is not None or method is not None):
        raise ValueError("Can't specify raw request and request method/headers together")
    if target and cachebrowse:
        raise ValueError("Can't specify target and use cachebrowse together")

    if cachebrowse is None:
        cachebrowse = True

    headers = headers or {}
    method = method or 'GET'

    if '://' not in url:
        url = scheme + '://' + url

    parsed_url = urlparse.urlparse(url, scheme=scheme)
    path = parsed_url.path or '/'

    if target:
        target, cachebrowsed = dns.resolve_host(target, use_cachebrowser_db=cachebrowse)
    else:
        target, cachebrowsed = dns.resolve_host(parsed_url.hostname, use_cachebrowser_db=cachebrowse)

    # if not cachebrowsed:
    # target = parsed_url.hostname

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if parsed_url.scheme == 'https':
        sock = ssl.wrap_socket(sock)
    sock.connect((target, port or (443 if parsed_url.scheme == 'https' else 80)))

    if raw_request is None:
        headers = headers or {}
        for header in headers.keys():
            if ':' in header:
                del headers[header]
        headers["Host"] = parsed_url.hostname

        http_request = httplib.HTTPConnection(target, 80)
        http_request.sock = sock
        http_request.request(method, path, headers=headers)
        http_request.response_class = HttpResponse
        response = http_request.getresponse()
    else:
        sock.send(raw_request)
        response = HttpResponse(sock, method=method)
        response.begin()

    return response


class HttpResponse(httplib.HTTPResponse):
    def __init__(self, sock, *args, **kwargs):
        httplib.HTTPResponse.__init__(self, sock, *args, **kwargs)
        self.header_buffer = StringIO.StringIO()

        class FPWrapper(object):
            def __init__(fself, fp):
                fself.fp = fp
                fself.read = fself.fp.read
                fself.close = fself.fp.close

            def readline(fself, *args, **kwargs):
                line = fself.fp.readline(*args, **kwargs)
                self.header_buffer.write(line)
                return line

        self.fp = FPWrapper(self.fp)
        self._header_pos = 0

    def read(self, amt=None, raw=False, *args, **kwargs):
        if not raw:
            return httplib.HTTPResponse.read(self, amt=amt)

        if self._header_pos == self.header_buffer.len:
            return httplib.HTTPResponse.read(self, amt=amt)
        self.header_buffer.seek(self._header_pos)
        res = self.header_buffer.read(amt)
        self._header_pos = self.header_buffer.pos
        return res

    def recv(self, *args, **kwargs):
        return self.read(raw=True, *args, **kwargs)


class HttpRequest(object):
    class Builder(object):
        def __init__(self):
            self._buffer = StringIO.StringIO()
            self._state = 'request'
            self._pos = 0
            self.content_length = 0
            self.http_request = HttpRequest()

        def is_ready(self):
            return self._state == 'done'

        def write(self, data):
            self._buffer.seek(0, os.SEEK_END)
            self._buffer.write(data)
            self._parse()

        def _parse(self):
            while self._pos != self._buffer.len:
                self._buffer.seek(self._pos)

                if self._state == 'body':
                    self._buffer.seek(self._pos)
                    # FIXME: Efficiency
                    data = self._buffer.read()
                    self.content_length -= len(data)
                    self.http_request.body += data
                    self._pos = self._buffer.pos
                    self.http_request.raw = self._buffer.getvalue()

                    if self.content_length <= 0:
                        self._state = 'done'

                    return self.http_request

                line = self._buffer.readline()
                if not line.endswith('\n'):
                    return

                self._pos = self._buffer.pos

                if self._state == 'request':
                    match = re.match("(GET|POST|PUT|DELETE|HEAD) (.+) \w+", line)
                    if match is None:
                        raise ValueError("Invalid request line: %s" % line)
                    self.http_request.method = match.group(1)
                    self.http_request.path = match.group(2)
                    self._state = 'headers'
                elif self._state == 'headers':
                    match = re.match("^\s*$", line)
                    if match is not None:
                        if self.content_length:
                            self._state = 'body'
                            continue
                        else:
                            self._state = 'done'
                            self.http_request.raw = self._buffer.getvalue()
                            return self.http_request

                    match = re.match("(.+): (.+)", line)
                    if match is None:
                        raise ValueError("Invalid header: %s" % line)
                    self.http_request.headers[match.group(1)] = match.group(2)
                    if match.group(1).lower() == 'content-length':
                        self.content_length = int(match.group(2))

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
                buff.write('%s: %s\r\n' % (header, self.headers[header].strip()))  # strip is important
            buff.write('\r\n')
            if self.body:
                buff.write(self.body)
            self.raw = buff.getvalue()
        return self.raw


class HttpConnection(object):
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

