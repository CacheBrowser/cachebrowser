import json
import unittest
import mock
from cachebrowser.api import BaseAPIHandler, ResponseOptions

# TODO Write tests for the API methods


class BaseAPIHandlerTest(unittest.TestCase):
    JSON_RESPONSE = {'some': 'thing'}

    def setUp(self):
        self.handler = BaseAPIHandler()
        self.handler.register_api('GET', '/path/get/1', self.get_one)
        self.handler.register_api('GET', '/path/get/2', self.get_two)
        self.handler.register_api('POST', '/path/post/1', self.post_one)
        self.handler.register_api('POST', '/path/post/2/', self.post_two)

    @staticmethod
    def get_one(request):
        return BaseAPIHandlerTest.JSON_RESPONSE

    @staticmethod
    def get_two(request):
        return request['value1'], ResponseOptions(send_json=False)

    @staticmethod
    def post_one(request):
        return BaseAPIHandlerTest.JSON_RESPONSE

    @staticmethod
    def post_two(request):
        return {'response': request['value1']}

    def test_get_no_param(self):
        request = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/path/get/1/',
            'QUERY_STRING': ''
        }

        start_response = mock.MagicMock()
        response = ''.join(self.handler.on_request(request, start_response))

        start_response.assert_called_once_with('200 OK', [('Content-Type', 'application/json')])
        self.assertEqual(BaseAPIHandlerTest.JSON_RESPONSE, json.loads(response))

    def test_get_with_no_json(self):
        request = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/path/get/2',
            'QUERY_STRING': 'value1=thefirstvalue&value2=10'
        }

        start_response = mock.MagicMock()
        response = ''.join(self.handler.on_request(request, start_response))

        start_response.assert_called_once_with('200 OK', [('Content-Type', 'text/plain')])
        self.assertEqual('thefirstvalue', response)

    def test_post_with_no_body(self):

        request = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/path/post/1',
            'QUERY_STRING': ''
        }

        start_response = mock.MagicMock()
        response = ''.join(self.handler.on_request(request, start_response))

        start_response.assert_called_once_with('200 OK', [('Content-Type', 'application/json')])
        self.assertEqual(BaseAPIHandlerTest.JSON_RESPONSE, json.loads(response))

    def test_post_with_body(self):
        request = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/path/post/2',
            'QUERY_STRING': '',
            'wsgi.input': json.dumps({'value1': 'thefirstvalue', 'value2': 10})
        }

        start_response = mock.MagicMock()
        response = ''.join(self.handler.on_request(request, start_response))
        start_response.assert_called_once_with('200 OK', [('Content-Type', 'application/json')])
        self.assertEqual({'response': 'thefirstvalue'}, json.loads(response))

    def test_invalid_path(self):
        request = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/this/does/not/exist',
            'QUERY_STRING': ''
        }

        start_response = mock.MagicMock()
        response = ''.join(self.handler.on_request(request, start_response))

        self.assertEqual(1, start_response.call_count)
        self.assertEqual('404 Not Found', start_response.call_args[0][0])
        self.assertEqual('', response)