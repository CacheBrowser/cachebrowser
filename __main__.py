import argparse
import logging
import sys
import cli
import proxy

from settings import settings
from daemon import Daemon
import eventloop
import api
import models


def parse_arguments():
    parser = argparse.ArgumentParser(description="CacheBrowser")
    parser.add_argument('-d', '-daemon', dest='daemon', help="run in daemon mode")
    parser.add_argument('-s', '-socket', dest='socket', help="cachebrowser socket")

    args = parser.parse_args()
    settings.update_from_args(vars(args))


def init_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)


def run_cachebrowser():
    logging.info("Cachebrowser running...")
    logging.debug("Waiting for connections...")

    models.initialize_database('/tmp/cachebrowser.db')
    looper = eventloop.looper
    looper.register_server(4242, api.handle_connection)
    looper.register_server(5001, cli.handle_connection)
    looper.register_server(5002, proxy.handle_connection)

    looper.start()


if __name__ == '__main__':
    parse_arguments()
    init_logging()
    if settings.get('daemon', False):
        daemon = Daemon('/tmp/cachebrowser.pid', run_cachebrowser)
        daemon.start()
    else:
        run_cachebrowser()