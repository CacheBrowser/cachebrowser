from __future__ import print_function, absolute_import

import mitmproxy
import mitmproxy.controller
from mitmproxy.proxy.server import ProxyServer

from cachebrowser.bootstrap import initialize_bootstrapper
from cachebrowser.resolver import Resolver
from .proxy import ProxyController
from .log import LogPipe

from .models import initialize_database


def cdnreaper(args=None):
    initialize_database('db.sqlite')
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
    cdnreaper()