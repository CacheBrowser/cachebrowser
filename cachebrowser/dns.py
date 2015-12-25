import socket

from cachebrowser.models import CDN, Host


def resolve_host(hostname, use_cachebrowser_db=True):
    # Check if host exists in database
    if use_cachebrowser_db:
        try:
            host = Host.get(hostname=hostname)
            cdn = host.cdn

            if cdn is None:
                _bootstrap_host(host)

            if not cdn.edge_server:
                _bootstrap_cdn(cdn)

            return cdn.edge_server, True
        except Host.DoesNotExist:
            pass
    return _dns_request(hostname), False


def _bootstrap_host(host):
    pass


def _bootstrap_cdn(cdn):
    pass


def _dns_request(hostname):
    return socket.gethostbyname(hostname)
