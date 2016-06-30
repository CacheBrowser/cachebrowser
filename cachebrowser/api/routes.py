from handlers.bootstrap import get_hosts, delete_host, add_host, add_cdn
from handlers.process import close, ping

routes = [
    ('/close', close),
    ('/ping', ping),
    ('/hosts', get_hosts),
    ('/hosts/delete', delete_host),
    ('/hosts/add', add_host),
    ('/cdns/add', add_cdn)
]
