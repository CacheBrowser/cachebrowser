import logging
from models import Host, CDN

_host_db = {
    'nbc.com': 'akamai',
    'www.nbc.com': 'akamai',
    'www.bloomberg.com': 'akamai',
    'www.wsj.com': 'akamai',
    'www.change.org': 'cloudfare',
    'www.surfeasy.com': 'cloudfare',
    'www.istockphoto.com': 'akamai',
    'www.tipico.com': 'akamai'
}

_cdn_db = {
    'akamai': ['192.189.138.182', '69.31.76.91', '23.208.91.198',  '23.218.210.7'],
    'cloudfare': ['104.16.4.13']
}


def bootstrap_host(hostname):
    if hostname not in _host_db:
        logging.info("Host %s could not be bootstrapped" % hostname)
        return False

    cdn_id = _host_db[hostname]

    try:
        cdn = CDN.get(id=cdn_id)
    except CDN.DoesNotExist:
        bootstrap_cdn(cdn_id)
        cdn = CDN.get(id=cdn_id)

    Host.create(url=hostname, cdn=cdn)

    return True


def bootstrap_cdn(cdn_id):
    if cdn_id not in _cdn_db:
        logging.info("CDN %s could not be bootstrapped" % cdn_id)
    addresses = _cdn_db[cdn_id]
    CDN.create(id=cdn_id, name=cdn_id, addresses=addresses)
