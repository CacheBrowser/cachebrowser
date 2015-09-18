from . import options
import threading
import core
from .daemon import Daemon
import argparse
import logging
import sys
import os
import socket


def parse_arguments():
    parser = argparse.ArgumentParser(description="CacheBrowser")
    parser.add_argument('-d', '-daemon', dest='daemon', help="run in daemon mode")
    parser.add_argument('-s', '-socket', dest='socket', help="cachebrowser socket")

    args = parser.parse_args()
    options.update_from_args(vars(args))


def init_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)


def run_cachebrowser():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    socket_name = options.get_or_error('socket')

    try:
        os.remove(socket_name)
    except OSError:
        pass

    logging.info("Cachebrowser running...")
    logging.debug("Waiting for connections...")

    sock.bind(socket_name)
    sock.listen(1)

    while True:
        connection, address = sock.accept()

        def handle():
            core.handle_connection(connection, address)

        threading.Thread(target=handle).start()

if __name__ == '__main__':
    parse_arguments()
    init_logging()
    if options.get('daemon', False):
        daemon = Daemon('/tmp/cachebrowser.pid', run_cachebrowser)
        daemon.start()
    else:
        run_cachebrowser()