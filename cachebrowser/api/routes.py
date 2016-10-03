from cachebrowser.api.handlers.bootstrap import get_hosts, get_cdns, delete_host, add_host, add_cdn
from cachebrowser.api.handlers.process import close, ping
from cachebrowser.api.handlers.website import is_website_enabled, enable_website, disable_website

routes = [
    ('/close', close),
    ('/ping', ping),
    ('/hosts', get_hosts),
    ('/hosts/delete', delete_host),
    ('/hosts/add', add_host),
    ('/cdns', get_cdns),
    ('/cdns/add', add_cdn),
    ('/website/enabled', is_website_enabled),
    ('/website/enable', enable_website),
    ('/website/disable', disable_website),
]
