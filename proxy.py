import logging
import socket

_pairs = {}


def handle_downstream(connection, message, looper):
    print(message)
    downstream_connection = _pairs[connection.fileno()]
    downstream_connection.send(message)


def handle_upstream(connection, message, looper):
    host = message.split('\n')[0].split(' ')[1]
    host = host.replace("http://", "").replace('/', '')
    print("Connecting to %s " % host)
    upstream_connection = create_connection(host, 80)
    _pairs[upstream_connection.fileno()] = connection
    looper.register_socket(upstream_connection, handle_downstream)
    upstream_connection.send(message)
    print(message)


def handle_connection(connection, addr, looper):
    logging.debug("New proxy connection established with %s" % str(addr))
    looper.register_socket(connection, handle_upstream)


def create_connection(host, port):
    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sock.setblocking(0)
    # sock.connect()
    return socket.create_connection((host, port))
