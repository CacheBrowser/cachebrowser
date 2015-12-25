import argparse
import sys
import gevent
from gevent import monkey

from cachebrowser.network import ServerRack, HttpServer
from cachebrowser.settings import settings
from cachebrowser.daemon import Daemon
from cachebrowser import models, http, cli, api, proxy, common, bootstrap
from cachebrowser.common import logger

rack = ServerRack()


def parse_arguments():
    parser = argparse.ArgumentParser(description="CacheBrowser")
    parser.add_argument('-d', '-daemon', action='store_true', dest='daemon', help="run in daemon mode")
    parser.add_argument('-s', '-socket', dest='socket', help="cachebrowser socket")
    parser.add_argument('-b', '-bootstrap', nargs="+", dest='local_bootstrap', help="local bootstrap source")
    parser.add_argument('command', nargs='*', default=None, help='A cachebrowser command to execute and exit')
    args = parser.parse_args()
    settings.update_from_args(vars(args))


def init_logging():
    import logging
    root = logger
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)


def load_extensions():
    import cachebrowser.extensions


def run_cachebrowser():
    logger.info("Cachebrowser running...")
    logger.debug("Waiting for connections...")

    monkey.patch_all()

    rack.create_server('cli', port=5100, handler=cli.CLIHandler)
    rack.add_server('api', HttpServer(port=5200, handler=api.APIHandler))
    rack.create_server('proxy', port=8080, handler=proxy.ProxyConnection)
    rack.create_server('http', port=9005, handler=http.HttpConnection)

    common.context['server_rack'] = rack
    load_extensions()

    rack.start_all()

    gevent.wait()


def run_command(command):
    class InlineCLIHandler(cli.CLIHandler):
        def __init__(self):
            super(InlineCLIHandler, self).__init__(None)
            self.send = sys.stdout.write

    handler = InlineCLIHandler()
    handler.handle_command(*command)


def main():
    parse_arguments()
    init_logging()
    models.initialize_database(settings['database'])
    bootstrap.initialize_bootstrapper()

    command = settings.get('command', None)
    if command:
        run_command(command)
        return

    if settings.get('daemon', False):
        daemon = Daemon('/tmp/cachebrowser.pid', run_cachebrowser)
        daemon.start()
    else:
        run_cachebrowser()

if __name__ == '__main__':
    __package__ = ''
    main()
