import socket
import gevent
from gevent.server import StreamServer


class ServerRack(object):
    def __init__(self):
        self.servers = {}
        self._greenlets = []

    def add_server(self, name, port, handler, ip=None):
        if not ip:
            ip = '0.0.0.0'
        server = Server(name, ip, port, handler)
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
    def __init__(self, name, ip, port, handler=None):
        self.name = name
        self.server = StreamServer((ip, port), self._handle)
        self.handler = handler

    def start(self):
        return self.server.start()

    def stop(self):
        self.server.stop()

    def _handle(self, sock, address):
        if self.handler:
            self.handler(sock, address=address).loop()


class Connection(object):
    def __init__(self, sock, address=None, *args, **kwargs):
        self.socket = sock
        self.address = address
        self.alive = True

        self._read_size = 1024

    def loop(self):
        self.on_connect()
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

    def on_connect(self):
        pass

    def on_data(self, data):
        pass

    def on_close(self):
        pass

    def on_error(self, error):
        pass
