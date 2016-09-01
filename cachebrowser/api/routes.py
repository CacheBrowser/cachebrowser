from cachebrowser.api.handlers.bootstrap import get_hosts, get_cdns, delete_host, add_host, add_cdn
from cachebrowser.api.handlers.process import close, ping

routes = [
    ('/close', close),
    ('/ping', ping),
    ('/hosts', get_hosts),
    ('/hosts/delete', delete_host),
    ('/hosts/add', add_host),
    ('/cdns', get_cdns),
    ('/cdns/add', add_cdn),
]
