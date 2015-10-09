import httplib
import ssl
import urlparse
from cachebrowser import dns


def request(url, method='GET', port=None, scheme='http'):
    if '://' not in url:
        url = scheme + '://' + url
    parsed_url = urlparse.urlparse(url, scheme)

    target, cachebrowsed = dns.resolve_host(parsed_url.hostname)
    if not cachebrowsed:
        target = parsed_url.hostname

    connection = None
    if parsed_url.scheme == 'http':
        connection = httplib.HTTPConnection(target, port or 80)
    elif parsed_url.scheme == 'https':
        connection = httplib.HTTPSConnection(target, port or 443, context=ssl._create_unverified_context())
    else:
        # TODO: Error
        pass

    connection.putrequest(method, parsed_url.path, skip_host=True)
    connection.putheader("Host", parsed_url.hostname)
    connection.putheader("Connection", "Close")
    connection.endheaders()

    return connection.getresponse().read()