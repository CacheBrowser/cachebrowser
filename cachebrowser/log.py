import logging

import colorama
from termcolor import colored

from cachebrowser.pipes.base import FlowPipe

colorama.init()

logger = logging.getLogger('cdnreaper')
# logger.addHandler(logging.FileHandler('clog', mode='w'))
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


class ProxyLogger(object):
    def __init__(self, level='debug'):
        self.level = level

        self.key_color_cache = {}
        self.colors = ['red', 'green', 'blue', 'magenta', 'cyan', 'grey', 'yellow']
        self.color_cnt = 0

    def get_key_color(self, key):
        if key not in self.key_color_cache:
            self.key_color_cache[key] = self.colors[self.color_cnt]
            self.color_cnt = (self.color_cnt + 1) % len(self.colors)

        return self.key_color_cache[key]

    def key_color(self, key, m):
        return colored(m, self.get_key_color(key), attrs=['bold'])

    def level_color(self, level, m):
        color = {
            'debug': 'cyan',
            'info': 'blue',
            'warning': 'yellow',
            'error': 'red'
        }.get(level.lower(), None)
        if color:
            return colored(m, color)
        return m

    def check_level(self, level):
        if level is None:
            return True

        level_order = [
            'debug',
            'info',
            'warning',
            'error'
        ]

        try:
            return level_order.index(level) >= level_order.index(self.level)
        except ValueError:
            return True

    def log(self, message, level=None, key=None):
        if not self.check_level(level):
            return

        s = ''
        if key is not None:
            if not type(key) == str:
                key = hex(id(key))[4:]
            s += '[{}] '.format(self.key_color(key, key), attrs=['bold'])
        if level:
            s += '[{}] '.format(self.level_color(level, level))
        s += str(message)
        # print(s)
        logger.info(s)


class LogPipe(FlowPipe):
    def serverconnect(self, server_conn):
        # self.publish('add_connection', {'server': server_conn.address.host})
        if server_conn.sni:
            self.log("{}  SNI: {}".format(server_conn.address, server_conn.sni), level="CONNECT", key=server_conn)
        else:
            self.log("{}".format(server_conn.address), level="CONNECT", key=server_conn)

    def request(self, flow):
        self.log("{}".format(flow.request.url), level=flow.request.method.upper(), key=flow.server_conn)


class LogPipe2(FlowPipe):
    def serverconnect(self, server_conn):
        if hasattr(server_conn, 'connection_recycle'):
            return server_conn
        if hasattr(server_conn, 'is_fake'):
            return server_conn
        self.publish('add_connection', {'server': server_conn.address.host, 'scrambled': True})
