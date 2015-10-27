import unittest
import gevent.server
from cachebrowser.http import HttpResponse


class HttpResponseTest(unittest.TestCase):
    HTML_DATA = '<html><body><h1>It works!</h1></body></html>'
    RAW_DATA = [
        'HTTP/1.1 200 OK\r\n',
        'Date: Sun, 18 Oct 2009 08:56:53 GMT\r\n',
        'Server: Apache/2.2.14 (Win32)\r\n',
        'Last-Modified: Sat, 20 Nov 2004 07:16:26 GMT\r\n',
        'Accept-Ranges: bytes\r\n',
        'Content-Length: 44\r\n',
        'Connection: close\r\n',
        'Content-Type: text/html\r\n',
        '\r\n',
        '%s\r\n' % HTML_DATA,
        '\r\n'
    ]

    class StubHttpServer(gevent.server.StreamServer):
        def handle(self, socket, address):
            for line in HttpResponseTest.RAW_DATA:
                socket.send(line)

    def setUp(self):
        self.server = HttpResponseTest.StubHttpServer(('127.0.0.1', 0))
        self.server.start()
        self.sock = gevent.socket.create_connection(('127.0.0.1', self.server.server_port))

    def tearDown(self):
        self.server.stop()

    def test_header(self):
        response = HttpResponse(self.sock)
        response.begin()

        self.assertEquals(200, response.status)
        self.assertEquals('OK', response.reason)

        headers = list(map(lambda (x,y): x, response.getheaders()))
        self.assertIn('date', headers)
        self.assertIn('connection', headers)

    def test_normal_read(self):
        response = HttpResponse(self.sock)
        response.begin()

        data = response.read()
        self.assertEquals(self.HTML_DATA, data)

    def test_raw_read(self):
        response = HttpResponse(self.sock)
        response.begin()

        all_data = ''
        while True:
            data = response.read(raw=True)
            if not data:
                break
            all_data += data
        self.assertEquals(''.join(self.RAW_DATA).strip(), all_data)

