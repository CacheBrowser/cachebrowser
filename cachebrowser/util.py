from termcolor import colored


class ColorCache(object):
    def __init__(self):
        self.cache = {}
        self.colors = ['red', 'green', 'blue', 'magenta', 'cyan', 'grey', 'yellow'] #'white',
        self.cnt = 0

    def get_color(self, key):
        if key not in self.cache:
            self.cache[key] = self.colors[self.cnt]
            self.cnt = (self.cnt + 1) % len(self.colors)

        return self.cache[key]


ccache = ColorCache()

def kcolor(text):

    # print(colored('something', 'blue', 'on_red'))
    return colored(text, ccache.get_color(text))


def get_flow_size(flow, ):
    """
    (Not accurate)
    """
    def get_size(r):
        s = len(r.content)
        for header in r.headers:
            s += len(header)
            s += len(r.headers[header])
            s += 1 # Colon (?)
        s += len(r.http_version)
        s += 2 # New lines
        return s

    if flow.request:
        req = get_size(flow.request) + len(flow.request.path) + len(flow.request.method)
    else:
        req = 0

    if flow.response:
        resp = get_size(flow.response) + len(flow.response.reason) + 3 # status code
    else:
        resp = 0

    return req, resp

def pretty_bytes(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
