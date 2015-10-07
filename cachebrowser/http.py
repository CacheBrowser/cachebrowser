import httplib
import urlparse
from cachebrowser import dns


def request(url, method='GET', scheme='http'):
    if '://' not in url:
        url = scheme + '://' + url
    parsed_url = urlparse.urlparse(url, scheme)

    target = dns.resolve_host(parsed_url.hostname)

    connection = None
    if parsed_url.scheme == 'http':
        connection = httplib.HTTPConnection(target)
    elif parsed_url.scheme == 'https':
        connection = httplib.HTTPSConnection(target)
    else:
        # TODO: Error
        pass

    connection.putrequest(method, parsed_url.path, skip_host=True)
    connection.putheader("Host", parsed_url.hostname)
    connection.putheader("Connection", "Close")
    connection.endheaders()

    return connection.getresponse().read()