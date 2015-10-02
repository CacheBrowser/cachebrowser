
def request_cdn_for_domain(domain):
    return {
        'nbc.com': 'akamai',
        'www.nbc.com': 'akamai',
        'www.bloomberg.com': 'akamai',
        'www.wsj.com': 'akamai',
        'www.change.org': 'cloudfare'
    }[domain]


def request_cdn_ips(cdn):
    return {
        'akamai': ['23.208.91.198'],#, '23.218.210.7'],
        'cloudfare': ['104.16.4.13']
    }[cdn]
