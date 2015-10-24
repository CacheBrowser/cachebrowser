import socket
from cachebrowser.network import Connection
import unittest
from mock import Mock, patch


class ServerTest(unittest.TestCase):
    def test_server(self):
        pass


class ConnectionTest(unittest.TestCase):
    def test_connection_handler(self):
        sock = Mock(spec=socket.socket)

        sock.recv = Mock(side_effect=['some data', ''])

        handler = Connection(sock, '1.2.3.4')
        handler.on_connect = Mock()
        handler.on_data = Mock()
        handler.on_close = Mock()
        handler.on_error = Mock()
        handler.loop()

        handler.on_connect.assert_called_once_with()
        handler.on_data.assert_called_once_with('some data')
        handler.on_close.assert_called_once_with()
        handler.on_error.assert_not_called()

        sock.recv = Mock(side_effect=socket.error)
        handler = Connection(sock, '1.2.3.4')
        handler.on_error = Mock()
        handler.loop()
        assert handler.on_error.called


