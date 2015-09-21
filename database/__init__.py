from database.sqlite import SqliteDatabase

database = SqliteDatabase()


def get_cdn_for_domain(domain):
    """
    Retrieve the cdn used for a domain from the cache database if it exists
    :param domain:
    :return:
    """
    return database.get_cdn_for_domain(domain)


def get_cdn_ips(cdn):
    """
    Retrieve a list of the CDNs ip addresses
    :param cdn:
    :return:
    """
    return database.get_cdn_ips(cdn)


def add_cdn_for_domain(domain, cdn):
    return database.add_cdn_for_domain(domain, cdn)


def add_cdn_ip(cdn, ip):
    return database.add_cdn_ip(cdn, ip)
