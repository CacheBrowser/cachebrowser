from models import CDN, Host
import socket

def resolve_host(hostname):
    # Check if host exists in database

    try:
        host = Host.get(hostname)
        cdn = host.cdn

        if cdn is None:
            _bootstrap_host(host)

        addresses = cdn.addresses
        if addresses is None or len(addresses) == 0:
            _bootstrap_cdn(cdn)

        return cdn.addresses[0]  # make it random?
    except Host.DoesNotExist:
        return _dns_request(hostname)


def _bootstrap_host(host):
    pass


def _bootstrap_cdn(cdn):
    pass


def _dns_request(hostname):
    return socket.gethostbyname(hostname)
