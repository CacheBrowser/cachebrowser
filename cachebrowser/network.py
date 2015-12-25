import inspect
import socket
import gevent
import gevent.pywsgi
from gevent.server import StreamServer


class ServerRack(object):
    def __init__(self):
        self.servers = {}
        self._greenlets = []

    def create_server(self, name, port, handler, ip=None):
        if not ip:
            ip = '0.0.0.0'
        server = Server(ip, port, handler)
        self.add_server(name, server)
        return server

    def add_server(self, name, server):
        self.servers[name] = server
        return server

    def get_server(self, name):
        return self.servers.get(name, None)

    def start_all(self):
        self._greenlets = []
        for server in self.servers.values():
            self._greenlets.append(server.start())

    def stop_all(self):
        for server in self.servers.values():
            server.stop()

    def join(self):
        # TODO: only wait on the racks greenlets
        gevent.wait()


class Server(object):
    def __init__(self, ip, port, handler=None):
        self.server = StreamServer((ip, port), self._handle)
        self.handler = handler

    def start(self):
        return self.server.start()

    def stop(self):
        self.server.stop()

    def _handle(self, sock, address):
        if self.handler is None:
            return

        if inspect.isclass(self.handler):
            return self.handler().loop(sock, address=address)
        else:
            return self.handler.loop(sock, address=address)


class ConnectionHandler(object):
    def __init__(self, *args, **kwargs):
        self.socket = None
        self.address = None
        self.alive = True

        self._read_size = 1024

    def loop(self, sock, address):
        self.socket = sock
        self.address = address
        self.alive = True

        self.on_connect(sock, address)
        self._loop_on_socket()

    def _loop_on_socket(self):
        try:
            while self.alive:
                buff = self.socket.recv(self._read_size)

                if len(buff) == 0:
                    self.alive = False
                    self.on_close()
                    break

                self.on_data(buff)
        except socket.error as e:
            self.alive = False
            self.on_error(e)

    def send(self, data):
        self.socket.send(data)

    def close(self):
        self.socket.close()

    def on_connect(self, sock, address):
        pass

    def on_data(self, data):
        pass

    def on_close(self):
        pass

    def on_error(self, error):
        pass


class HttpServer(object):
    def __init__(self, port, host='', handler=None):
        self.port = port
        self.host = host

        self.handler = handler

        self.server = gevent.pywsgi.WSGIServer(
            (self.host, self.port), self._handle)

    def start(self):
        return self.server.start()

    def stop(self):
        self.server.stop()

    def _handle(self, env, start_response):
        if self.handler is None:
            start_response('404 Not Found', [])
            return ['']
        if inspect.isclass(self.handler):
            return self.handler().on_request(env, start_response)
        else:
            return self.handler.on_request(env, start_response)


class HttpConnectionHandler(object):
    def on_request(self, env, start_response):
        pass