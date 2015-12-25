import traceback
from six.moves import urllib_parse as urlparse

context = {}


def extract_url_hostname(url):
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
                    _get_logger().error(traceback.format_exc())

        return inner
    return outer


def _get_logger():
    import logging
    return logging.getLogger('cachebrowser')

logger = _get_logger()