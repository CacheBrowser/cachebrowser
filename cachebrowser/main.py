from __future__ import print_function, absolute_import

import mitmproxy
import mitmproxy.controller
from mitmproxy.proxy.server import ProxyServer

from cachebrowser.bootstrap import Bootstrapper
from cachebrowser.log import LogPipe
from cachebrowser.models import initialize_database
from cachebrowser.proxy import ProxyController
from cachebrowser.resolver import Resolver
from cachebrowser.settings import DevelopmentSettings, ProductionSettings


def cachebrowser(args=None, dev=False):
    settings = DevelopmentSettings() if dev else ProductionSettings()

    # TODO update settings with config file
    # TODO udpate settings with args

    if not dev:
        check_data_files(settings)

    initialize_database(settings.database)
    bootstrapper = Bootstrapper(settings)

    config = mitmproxy.proxy.ProxyConfig(port=settings.port)
    server = ProxyServer(config)
    m = ProxyController(server)
    m.add_pipe(LogPipe())
    m.add_pipe(Resolver(bootstrapper))
    # m.add_pipe(Scrambler())
    try:
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
            # TODO err
            return

    data_files = [
        'local_bootstrap.yaml'
    ]

    for data_file in data_files:
        data_path = settings.data_path(data_file)

        if not os.path.isfile(data_path):
            # TODO LOG
            print("Creating data file {}".format(data_path))
            with open(data_path, 'w') as f:
                f.write(pkgutil.get_data('cachebrowser', os.path.join('data', data_file)))


if __name__ == '__main__':
    cachebrowser()
