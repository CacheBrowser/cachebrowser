from __future__ import print_function, absolute_import

import mitmproxy
import mitmproxy.controller
from mitmproxy.proxy.server import ProxyServer

from cachebrowser.bootstrap import initialize_bootstrapper
from cachebrowser.log import LogPipe
from cachebrowser.models import initialize_database
from cachebrowser.proxy import ProxyController
from cachebrowser.resolver import Resolver
from cachebrowser.settings import settings


def cachebrowser(args=None):
    initialize_database(settings.database)
    initialize_bootstrapper()

    config = mitmproxy.proxy.ProxyConfig(port=8080)
    server = ProxyServer(config)
    m = ProxyController(server)
    m.add_pipe(LogPipe())
    m.add_pipe(Resolver())
    # m.add_pipe(Scrambler())
    try:
        return m.run()
    except KeyboardInterrupt:
        m.shutdown()


if __name__ == '__main__':
    cachebrowser()
