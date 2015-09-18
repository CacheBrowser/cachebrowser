
def request_cdn_for_domain(domain):
    return {
        'nbc.com': 'akamai',
        'www.nbc.com': 'akamai'
    }[domain]


def request_cdn_ips(cdn):
    return {
        'akamai': ['192.189.138.251']#, '23.218.210.7']
    }[cdn]
