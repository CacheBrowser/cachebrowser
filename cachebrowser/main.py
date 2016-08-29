from __future__ import print_function, absolute_import

import logging
import logging.config
import sys

import mitmproxy
import mitmproxy.controller
from mitmproxy.proxy.server import ProxyServer


from cachebrowser.bootstrap import Bootstrapper
from cachebrowser.models import initialize_database
from cachebrowser.proxy import ProxyController
from cachebrowser.pipes.resolver import Resolver
from cachebrowser.pipes.publisher import Publisher
from cachebrowser.settings import DevelopmentSettings, ProductionSettings
from cachebrowser.ipc import IPCManager

logger = logging.getLogger(__name__)


def initialize_logging():
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,  # this fixes the problem

        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level':'INFO',
                'class':'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': True
            }
        }
    })


def cachebrowser(args=None, dev=False):
    settings = DevelopmentSettings() if dev else ProductionSettings()

    # TODO update settings with config file
    # TODO udpate settings with args

    initialize_logging()

    if not dev:
        check_data_files(settings)

    logger.debug("Initializing database")
    initialize_database(settings.database)

    logger.debug("Initializing bootstrapper")
    bootstrapper = Bootstrapper(settings)

    logger.debug("Initializing IPC")
    ipc = IPCManager(settings)

    config = mitmproxy.proxy.ProxyConfig(port=settings.port)
    server = ProxyServer(config)
    m = ProxyController(server, ipc)

    logger.debug("Adding 'Resolver' pipe")
    m.add_pipe(Resolver(bootstrapper))
    logger.debug("Adding 'Publisher' pipe")
    m.add_pipe(Publisher())

    try:
        logger.info("Listening for proxy connections on port {}".format(settings.port))
        return m.run()
    except KeyboardInterrupt:
        m.shutdown()


def check_data_files(settings):
    import os
    import pkgutil

    if not os.path.isdir(settings.data_dir()):
        try:
            os.mkdir(settings.data_dir())
        except OSError:
            logger.error("Creating data directory failed", exc_info=True)
            sys.exit(1)

    data_files = [
        'local_bootstrap.yaml'
    ]

    for data_file in data_files:
        data_path = settings.data_path(data_file)

        if not os.path.isfile(data_path):
            logger.info("Creating data file {}".format(data_path))
            with open(data_path, 'w') as f:
                f.write(pkgutil.get_data('cachebrowser', os.path.join('data', data_file)))


if __name__ == '__main__':
    cachebrowser()
    import mitmproxy.protocol.tls
    import mitmproxy.controller
