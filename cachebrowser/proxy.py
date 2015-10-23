import threading
import urlparse
from cachebrowser import http
from cachebrowser.models import Host
from common import silent_fail
import logging
import socket
import ssl
import StringIO
import re
import dns


_connections = {}


def handle_connection(sock, addr, looper):
    logging.debug("New proxy connection established with %s" % str(addr))
    sock.setblocking(1)
    connection = ProxyConnection(looper, sock)
    # looper.register_socket(sock, connection.on_upstream_data, connection.on_local_closed)

    def run():
        try:
            while True:
                buf = sock.recv(1024)
                connection.on_upstream_data(buf)
                if not len(buf):
                    connection.on_local_closed()
                    break
        except:
            pass

    t = threading.Thread(target=run)
    t.daemon = True
    t.start()


def _connect(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sock.setblocking(0)
    # Blocking for now
    try:
        sock.connect((ip, port))
    except socket.error:
        pass
    return sock


class ProxyConnection(object):
    def __init__(self, looper, sock):
        self._looper = looper
        self._buffer = StringIO.StringIO()
        self._schema = None
        self._local_socket = sock
        self._remote_socket = None

    @silent_fail(log=True)
    def on_upstream_data(self, data):
        if len(data) == 0:
            return
        # print("------- UP -------")
        # print(data)
        # print("------------------")

        if self._schema is not None:
            return self._schema.on_upstream_data(data)
        self._buffer.write(data)

        # Check for schema
        schema = self._check_for_schema()
        if schema is not None:
            self._schema = schema(self, self._looper, self._buffer)

    @silent_fail(log=True)
    def on_downstream_data(self, data):
        if len(data) == 0:
            return
        # print("------- DOWN -------")
        # print(data)
        # print("------------------")
        if hasattr(self._schema, 'on_downstream_data'):
            return self._schema.on_downstream_data(data)

        self.send_downstream(data)

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

    def send_upstream(self, data):
        if len(data) == 0:
            return
        self._remote_socket.send(data)

    def send_downstream(self, data):
        if len(data) == 0:
            return
        self._local_socket.send(data)

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
    def __init__(self, connection, looper, buff):
        self._connection = connection
        self._looper = looper
        self._upstream_started = False
        self.request_builder = http.HttpRequest.Builder()
        self._start_upstream(buff)

    def on_upstream_data(self, data):
        if not self._upstream_started:
            self.request_builder.write(data)
            self._check_request()
            return

        # self._connection.send_upstream(data)

    def _start_upstream(self, buff):
        self.request_builder.write(buff.getvalue())
        self._check_request()

    def _check_request(self):
        if not self.request_builder.is_ready():
            return
        self._upstream_started = True

        def callback(response):
            # If is a redirect, switch https with http
            if 'Location: ' in response:
                response = response.replace('Location: https', 'Location: http')
            self._connection.on_downstream_data(response)

        http_request = self.request_builder.http_request

        url = http_request.path
        parsed_url = urlparse.urlparse(url)
        cachebrowsed = False
        try:
            Host.get(url=parsed_url.hostname)
            url = url.replace('http', 'https')
            cachebrowsed = True
        except Host.DoesNotExist:
            pass

        logging.info("[%s] %s %s" % (http_request.method, url, '<CACHEBROWSED>' if cachebrowsed else ''))
        http.request(url, method=http_request.method, headers=http_request.headers, stream=True, callback=callback)

        # def _connect_upstream(self, host):
        # # sock = _connect(host, 80)
        #     ip, cachebrowsed = dns.resolve_host(host)
        #     if not ip:
        #         return
        #
        #     # sock = _connect(ip, port)
        #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #     sock = ssl.wrap_socket(sock)
        #     sock.connect((ip, 80))
        #
        #     self._looper.register_socket(sock, self._connection.on_downstream_data, self._connection.on_remote_closed)
        #     self._connection._remote_socket = sock
        #
        #     self._buffer.seek(0)
        #     self._connection.send_upstream(self._buffer.getvalue())
        #
        #     self._upstream_started = True
        #     self._host = host
        #
        #     return True


class SSLSchema(object):
    def __init__(self, connection, looper, buff):
        # self._connection = connection
        # self._looper = looper
        # self._buffer = buff
        # self._upstream_started = False
        # self._host = None
        # self._start_upstream()
        connection._local_socket.close()

    def on_upstream_data(self, data):
        if not self._upstream_started and not self._start_upstream():
            self._buffer.seek(0, 2)
            self._buffer.write(data)
            return

        self._connection.send_upstream(data)

    def _start_upstream(self):
        self._buffer.seek(0)
        firstline = self._buffer.readline()
        match = re.match("(?:CONNECT) ([^:]+)(?:[:](\d+))? \w+", firstline)
        if match is None:
            return

        host = match.group(1)
        port = int(match.group(2) or 443)

        logging.info("[HTTPS] %s:%s" % (host, port))

        return self._connect_upstream(host, port)

    def _connect_upstream(self, host, port):
        ip, cachebrowsed = dns.resolve_host(host)
        if not ip:
            return

        # sock = _connect(ip, port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = ssl.wrap_socket(sock)
        sock.connect((ip, port))

        self._looper.register_socket(sock, self._connection.on_downstream_data, self._connection.on_remote_closed)
        self._connection._remote_socket = sock

        self._upstream_started = True
        self._host = host

        # ! Ref to _connection._buffer not updated
        self._buffer = StringIO.StringIO()

        self._connection.send_downstream("HTTP/1.1 200 OK\r\n\r\n")

        return True


        # class SSLSchema2(SSLSchema):
        # def __init__(self, connection, looper, buff):
        #         # super(SSLSchema2, self).__init__(*args, **kwargs)
        #         self._sslschema = SSLSchema(*args, **kwargs)
        #
        #     def on_upstream_data(self, data):
        #         if not self._upstream_started and not self._start_upstream():
        #             self._buffer.seek(0, 2)
        #             self._buffer.write(data)
        #             return

        # class SSLSchema2(object):
        #     def __init__(self, connection, looper, buff):
        #         self._connection = connection
        #         self._looper = looper
        #         self._buffer = buff
        #         self._upstream_started = False
        #         self._host = None
        #         self._start_upstream()
        #
        #     def on_upstream_data(self, data):
        #         if not self._upstream_started and not self._start_upstream():
        #             self._buffer.seek(0, 2)
        #             self._buffer.write(data)
        #             return
        #
        #         self._connection.send_upstream(data)
        #
        #     def _start_upstream(self):
        #         self._buffer.seek(0)
        #         firstline = self._buffer.readline()
        #         match = re.match("(?:CONNECT) ([^:]+)(?:[:](\d+))? \w+", firstline)
        #         if match is None:
        #             return
        #
        #         host = match.group(1)
        #         port = int(match.group(2) or 443)
        #
        #         logging.info("[HTTPS] %s:%s" % (host, port))
        #
        #         if not self._connect_upstream(host, port):
        #             return False
        #
        #         self._connection._local_socket = ssl.wrap_socket(self._connection._local_socket,
        #                                                          do_handshake_on_connect=False,
        #                                                          server_side=True,
        #                                                          certfile='/Users/hadi/Uni/Lab/cert/cert.pem',
        #                                                          keyfile='/Users/hadi/Uni/Lab/cert/key.pem')
        #
        #     def _connect_upstream(self, host, port):
        #         ip, cachebrowsed = dns.resolve_host(host)
        #         if not ip:
        #             return
        #
        #         # sock = _connect(ip, port)
        #         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #         sock = ssl.wrap_socket(sock)
        #         sock.connect((ip, port))
        #
        #         self._looper.register_socket(sock, self._connection.on_downstream_data, self._connection.on_remote_closed)
        #         self._connection._remote_socket = sock
        #
        #         self._upstream_started = True
        #         self._host = host
        #
        #         # ! Ref to _connection._buffer not updated
        #         self._buffer = StringIO.StringIO()
        #
        #         self._connection.send_downstream("HTTP/1.1 200 OK\r\n\r\n")
        #
        #         return True