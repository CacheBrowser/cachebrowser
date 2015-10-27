import unittest
import gevent.server
from mock import mock
from cachebrowser.proxy import ProxyConnection, HttpSchema


# class HttpProxyTest(unittest.TestCase):
#     REQUEST = [
#         'GET / HTTP/1.1\r\n',
#         'User-Agent: Wget/1.15 (linux)\r\n',
#         'HOST: www.google.com\r\n',
#         'Content-Length: 24\r\n',
#         '\r\n',
#         'something with 24 length',
#     ]
#     # class StubHttpServer(gevent.server.StreamServer):
#     #     def handle(self, socket, address):
#     #         for line in HttpResponseTest.RAW_DATA:
#     #             socket.send(line)
#
#
#     def test_http_schema(self):
#         connection = mock.Mock(spec=ProxyConnection)
#         http_schema = HttpSchema(connection)
#         http_schema.on_local_data(''.join(self.REQUEST[:3]))
#         http_schema.on_local_data(''.join(self.REQUEST[3:]))