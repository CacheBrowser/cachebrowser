from collections import defaultdict
import logging
import platform
import socket
import select
import traceback

__all__ = ['loop']

POLL_NULL = 0x00
POLL_IN = 0x01
POLL_OUT = 0x04
POLL_ERR = 0x08
POLL_HUP = 0x10
POLL_NVAL = 0x20


class EventLoop(object):
    def __init__(self, impl):
        if not impl:
            raise ValueError("No Event loop implementation specified")

        self._impl = impl()
        self._ = {}
        self._servers = set()
        self._sockets = {}

    def start(self):
        logging.debug("Starting event loop")
        self._run()

    def register_server(self, port, handler, ip=None):
        if not ip:
            ip = "0.0.0.0"

        sock = self._create_server_socket(ip, port)
        self.register_socket(sock, handler, None)
        self._servers.add(sock.fileno())

    def register_socket(self, sock, data_callback, close_callback):
        sock.setblocking(0)
        self._sockets[sock.fileno()] = (sock, data_callback, close_callback)
        self._register(sock.fileno())

    def _register(self, fd):
        self._impl.register(fd, POLL_IN)

    def _unregister(self, fd):
        self._impl.unregister(fd)

    def _run(self):
        try:
            while True:
                try:
                    events = self._impl.poll(1)
                    for fileno, event in events:
                        sock, data_handler, close_handler = self._sockets[fileno]
                        if fileno in self._servers:
                            connection, address = sock.accept()
                            data_handler(connection, address, self)
                        elif event & POLL_IN:
                            data = sock.recv(1024)
                            if data is None or len(data) == 0:
                                self._unregister(fileno)
                                close_handler()

                            data_handler(data)
                        elif event & POLL_HUP:
                            self._unregister(fileno)
                            sock.close()
                            close_handler()
                            del self._sockets[fileno]
                except socket.error:
                    traceback.format_exc()
        finally:
            for server in self._servers:
                self._unregister(server)
            self._impl.close()
            for server in self._servers:
                self._sockets[server][0].close()

    @staticmethod
    def _create_server_socket(ip, port):
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(128)
        sock.setblocking(0)
        return sock


class KqueueLoop(object):

    MAX_EVENTS = 1024

    def __init__(self):
        self._kqueue = select.kqueue()
        self._fds = {}

    def _control(self, fd, mode, flags):
        events = []
        if mode & POLL_IN:
            events.append(select.kevent(fd, select.KQ_FILTER_READ, flags))
        if mode & POLL_OUT:
            events.append(select.kevent(fd, select.KQ_FILTER_WRITE, flags))
        for e in events:
            self._kqueue.control([e], 0)

    def poll(self, timeout):
        if timeout < 0:
            timeout = None  # kqueue behaviour
        events = self._kqueue.control(None, KqueueLoop.MAX_EVENTS, timeout)
        results = defaultdict(lambda: POLL_NULL)
        for e in events:
            fd = e.ident
            if e.filter == select.KQ_FILTER_READ:
                results[fd] |= POLL_IN
            elif e.filter == select.KQ_FILTER_WRITE:
                results[fd] |= POLL_OUT
        return results.items()

    def register(self, fd, mode):
        self._fds[fd] = mode
        self._control(fd, mode, select.KQ_EV_ADD)

    def unregister(self, fd):
        self._control(fd, self._fds[fd], select.KQ_EV_DELETE)
        del self._fds[fd]

    def modify(self, fd, mode):
        self.unregister(fd)
        self.register(fd, mode)

    def close(self):
        self._kqueue.close()


_impl = None
_platform = platform.system()
if _platform == 'Darwin':
    _impl = KqueueLoop
elif _platform == 'Linux':
    _impl = select.epoll

looper = EventLoop(_impl)


def test_loop():
    def bar(connection, data):
        print("Message from %d: %s" % (connection.fileno(), data))

    def foo(connection, addr):
        looper.register_socket(connection, bar)
        print(addr)
    looper.register_server(6789, foo, '127.0.0.1')
    looper.start()