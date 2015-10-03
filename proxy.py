from common import silent_fail
import logging
import socket
import StringIO
import re
import dns


_connections = {}


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
        self._buffer = buff
        self._upstream_started = False
        self._host = None
        self._start_upstream()

    def on_upstream_data(self, data):
        if not self._upstream_started and not self._start_upstream():
            self._buffer.seek(0, 2)
            self._buffer.write(data)
            return

        self._connection.send_upstream(data)

    def _start_upstream(self):
        self._buffer.seek(0)
        firstline = self._buffer.readline()
        match = re.match("(?:GET|POST|PUT|DELETE|HEAD) (.+) \w+", firstline)
        if match is None:
            return

        url = match.group(1)

        logging.info("[HTTP] %s" % url)

        match = re.match("(?:http://)?([a-zA-Z0-9.]+)(?:[/?].*)?", url)
        if match is None:
            logging.warning("Invalid url '%s'" % url)
            return
        host = match.group(1)
        return self._connect_upstream(host)

    def _connect_upstream(self, host):
        sock = _connect(host, 80)
        self._looper.register_socket(sock, self._connection.on_downstream_data, self._connection.on_remote_closed)
        self._connection._remote_socket = sock

        self._buffer.seek(0)
        self._connection.send_upstream(self._buffer.getvalue())

        self._upstream_started = True
        self._host = host

        return True


class SSLSchema(object):
    def __init__(self, connection, looper, buff):
        self._connection = connection
        self._looper = looper
        self._buffer = buff
        self._upstream_started = False
        self._host = None
        self._start_upstream()

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
        ip = dns.resolve_host(host)
        if not ip:
            return

        sock = _connect(ip, port)
        self._looper.register_socket(sock, self._connection.on_downstream_data, self._connection.on_remote_closed)
        self._connection._remote_socket = sock

        self._upstream_started = True
        self._host = host

        # ! Ref to _connection._buffer not updated
        self._buffer = StringIO.StringIO()

        self._connection.send_downstream("HTTP/1.1 200 OK\r\n\r\n")

        return True


def handle_connection(sock, addr, looper):
    # logging.debug("New proxy connection established with %s" % str(addr))
    connection = ProxyConnection(looper, sock)
    looper.register_socket(sock, connection.on_upstream_data, connection.on_local_closed)


def _connect(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sock.setblocking(0)
    # Blocking for now
    try:
        sock.connect((ip, port))
    except socket.error:
        pass
    return sock
