from models import CDN, Host
import socket


def resolve_host(hostname, use_cachebrowser_db=True):
    # Check if host exists in database
    if use_cachebrowser_db:
        try:
            host = Host.get(hostname)
            cdn = host.cdn

            if cdn is None:
                _bootstrap_host(host)

            addresses = cdn.addresses
            if addresses is None or len(addresses) == 0:
                _bootstrap_cdn(cdn)

            return cdn.addresses[0], True  # make it random?
        except Host.DoesNotExist:
            pass
    return _dns_request(hostname), False


def _bootstrap_host(host):
    pass


def _bootstrap_cdn(cdn):
    pass


def _dns_request(hostname):
    return socket.gethostbyname(hostname)
