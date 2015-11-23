import socket
from gevent import monkey

from cachebrowser.network import ConnectionHandler, HttpServer, HttpConnectionHandler
import unittest
from mock import Mock, patch

monkey.patch_all()


class ServerTest(unittest.TestCase):
    def test_server(self):
        pass

    def test_connection_handler(self):
        sock = Mock(spec=socket.socket)

        sock.recv = Mock(side_effect=['some data', ''])

        handler = ConnectionHandler()
        handler.on_connect = Mock()
        handler.on_data = Mock()
        handler.on_close = Mock()
        handler.on_error = Mock()
        handler.loop(sock, '1.2.3.4')

        handler.on_connect.assert_called_once_with()
        handler.on_data.assert_called_once_with('some data')
        handler.on_close.assert_called_once_with()
        handler.on_error.assert_not_called()

        sock.recv = Mock(side_effect=socket.error)
        handler = ConnectionHandler()
        handler.on_error = Mock()
        handler.loop(sock, '1.2.3.4')
        assert handler.on_error.called


class HttpServerTest(unittest.TestCase):
    """
    Functional test to test WSGI HTTP server
    """

    PORT = 23456

    @classmethod
    def setUpClass(cls):
        cls.handler = HttpConnectionHandler()
        cls.server = HttpServer(cls.PORT, handler=cls.handler)
        cls.server.start()

    def make_get(self, path, query=None):
        import urllib2
        request = 'http://127.0.0.1:%d%s' % (self.PORT, path)
        if query:
            request = request + '?' + query

        urllib2.urlopen(request)

    def make_post(self, path, data=None):
        import urllib, urllib2
        if not data:
            data = {}
        encoded_data = urllib.urlencode(data)
        request = 'http://127.0.0.1:%d%s' % (self.PORT, path)
        urllib2.urlopen(request, data=encoded_data)

    def test_get_no_param(self):
        path = '/some/path'

        def on_request(env, start):
            self.assertEqual(path.strip('/'), env['PATH_INFO'].strip('/'))
            self.assertEqual('GET', env['REQUEST_METHOD'])
            start('200 OK', [])
            yield 'something'

        self.handler.on_request = on_request
        self.make_get(path)

    def test_get_with_param(self):
        path = '/some/path'
        query = 'value1=sth&value2=10'

        def on_request(env, start):
            self.assertEqual(query, env['QUERY_STRING'])
            start('200 OK', [])
            yield 'something'

        self.handler.on_request = on_request
        self.make_get(path, query)
