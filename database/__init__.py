import logging

domain_cdn = {}
cdn_ip = {}


def get_cdn_for_domain(domain):
    """
    Retrieve the cdn used for a domain from the cache database if it exists
    :param domain:
    :return:
    """
    try:
        return domain_cdn[domain]
    except KeyError:
        return None


def get_cdn_ips(cdn):
    """
    Retrieve a list of the CDNs ip addresses
    :param cdn:
    :return:
    """
    try:
        return cdn_ip[cdn]
    except KeyError:
        return None


def add_cdn_for_domain(domain, cdn):
    logging.debug("Add CDN %s for domain %s" % (cdn, domain))

    domain_cdn[domain] = cdn


def add_cdn_ip(cdn, ip):
    logging.debug("Add IP address(es) for CDN %s: %s" % (cdn, str(ip)))

    cdn_ip[cdn] = ip