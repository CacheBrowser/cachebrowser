import logging
import localdns
import bootstrapper
import database
import random
import urlparse


def add_domain(domain):
    """
    Add a domain to cachebrowser

    :param domain:
    :return:
    """

    domain = parse_url(domain)

    # If already exists in LocalDNS then skip
    if localdns.contains_record(domain):
        logging.info("Domain %s already exists in the LocalDNS, skipping add request" % domain)
        return

    # Check CacheDB to see if cdn for the domain exists
    # If it doesn't ask Bootstrapper to get it and add it to the db
    cdn = database.get_cdn_for_domain(domain)
    if not cdn:
        cdn = bootstrap_domain(domain)

    # Check CacheDB to see if IP addresses for the cdn exist
        # If it doesn't ask Bootstrapper to get it and add it to the db
    cdn_ip_list = database.get_cdn_ips(cdn)
    if not cdn_ip_list:
        cdn_ip_list = bootstrap_cdn(cdn)

    # TODO: If bootstrap failed

    # Select an ip from the list
    cdn_ip = cdn_ip_list[random.randint(0, len(cdn_ip_list) - 1)]

    # Add Record to LocalDNS
    localdns.add_record(domain, cdn_ip)


def bootstrap_domain(domain):
    cdn = bootstrapper.request_cdn_for_domain(domain)
    database.add_cdn_for_domain(domain, cdn)
    return cdn


def bootstrap_cdn(cdn):
    ip_list = bootstrapper.request_cdn_ips(cdn)
    database.add_cdn_ip(cdn, ip_list)
    return ip_list


def parse_url(url):
    if '://' not in url:
        url = '//' + url
    parsed = urlparse.urlparse(url)
    return parsed.netloc
