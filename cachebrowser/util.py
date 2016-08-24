import os
import importlib
import inspect

from termcolor import colored


class ColorCache(object):
    def __init__(self):
        self.cache = {}
        self.colors = ['red', 'green', 'blue', 'magenta', 'cyan', 'grey', 'yellow']
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
            # Colon
            s += 1
        s += len(r.http_version)
        # New lines
        s += 2
        return s

    if flow.request:
        req = get_size(flow.request) + len(flow.request.path) + len(flow.request.method)
    else:
        req = 0

    if flow.response:
        # status code
        resp = get_size(flow.response) + len(flow.response.reason) + 3
    else:
        resp = 0

    return req, resp


def pretty_bytes(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


class Data:
    def __init__(self, name):
        m = importlib.import_module(name)
        dirname = os.path.dirname(os.path.dirname(inspect.getsourcefile(m)))
        self.dirname = os.path.join(os.path.abspath(dirname), 'data')

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, path)
        if not os.path.exists(fullpath):
            raise ValueError("dataPath: %s does not exist." % fullpath)
        return fullpath
pkg_data = Data(__name__)
