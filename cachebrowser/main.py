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


if __name__ == '__main__':
    cachebrowser()
