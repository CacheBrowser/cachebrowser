import logging


class CacheBrowserDatabase(object):
    def get_cdn_for_domain(self, domain):
        """
        Retrieve the cdn used for a domain from the cache database if it exists
        :param domain:
        :return:
        """
        pass

    def get_cdn_ips(self, cdn):
        """
        Retrieve a list of the CDNs ip addresses
        :param cdn:
        :return:
        """
        pass

    def add_cdn_for_domain(self, domain, cdn):
        logging.debug("Add CDN %s for domain %s" % (cdn, domain))

    def add_cdn_ip(self, cdn, ip):
        logging.debug("Add IP address(es) for CDN %s: %s" % (cdn, str(ip)))


class MemoryDatabase(CacheBrowserDatabase):
    def __init__(self, *args, **kwargs):
        super(MemoryDatabase, self).__init__(*args, **kwargs)
        self.domain_cdn = {}
        self.cdn_ip = {}

    def get_cdn_for_domain(self, domain):
        """
        Retrieve the cdn used for a domain from the cache database if it exists
        :param domain:
        :return:
        """
        try:
            return self.domain_cdn[domain]
        except KeyError:
            return None

    def get_cdn_ips(self, cdn):
        """
        Retrieve a list of the CDNs ip addresses
        :param cdn:
        :return:
        """
        try:
            return self.cdn_ip[cdn]
        except KeyError:
            return None

    def add_cdn_for_domain(self, domain, cdn):
        self.domain_cdn[domain] = cdn

    def add_cdn_ip(self, cdn, ip):
        self.cdn_ip[cdn] = ip