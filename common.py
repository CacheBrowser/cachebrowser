from models import Host, CDN
import logging
import bootstrapper
import urlparse
import traceback


def add_domain(url):
    """
    Add a domain to cachebrowser

    :param url:
    :return:
    """

    host = _parse_url(url)

    # If already exists then skip
    try:
        Host.get(url=host)
        logging.info("Domain %s already exists in the LocalDNS, skipping add request" % host)
        return
    except Host.DoesNotExist:
        pass

    bootstrapper.bootstrap_host(host)

    return host


def is_host_active(url):
    host = _parse_url(url)
    try:
        Host.get(url=host)
        return True
    except Host.DoesNotExist:
        return False


def _parse_url(url):
    if '://' not in url:
        url = '//' + url
    parsed = urlparse.urlparse(url)
    return parsed.netloc


def silent_fail(log=False):
    def outer(func):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log:
                    logging.error(traceback.format_exc())

        return inner
    return outer