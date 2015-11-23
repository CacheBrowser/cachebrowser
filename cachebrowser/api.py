import urlparse
import json

from cachebrowser.network import HttpConnectionHandler
from cachebrowser import http
from cachebrowser import common


class ResponseOptions(object):
    def __init__(self, send_json=True, content_type=None, status=200, reason='OK'):
        self.send_json = send_json

        if content_type is not None:
            self.content_type = content_type
        else:
            self.content_type = 'application/json' if self.send_json else 'text/plain'

        self.status = status
        self.reason = reason or {
            200: 'OK',
            404: 'Not Found',
            403: 'Forbidden'
        }.get(self.status, '')


class BaseAPIHandler(HttpConnectionHandler):
    def __init__(self, *args, **kwargs):
        self.method_handlers = {}
        self.send_json = True

    @common.silent_fail(log=True)
    def on_request(self, env, start_response):
        method = env['REQUEST_METHOD'].upper()
        path = env['PATH_INFO'].lower().strip('/')

        if method not in self.method_handlers or path not in self.method_handlers[method]:
            start_response('404 Not Found', [])
            return

        if method == 'GET':
            request = urlparse.parse_qs(env.get('QUERY_STRING', ''), True)
            for query in request:
                if len(request[query]) == 1:
                    request[query] = request[query][0]
        else:
            request = json.loads(env.get('wsgi.input', '{}'))

        response = self.method_handlers[method][path](request)

        if type(response) == tuple:
            response, options = response
        else:
            options = ResponseOptions()

        start_response('%d %s' % (options.status, options.reason), [('Content-Type', options.content_type)])

        if options.send_json:
            yield json.dumps(response)
        else:
            yield response

    def register_api(self, method, path, handler):
        method = method.upper()
        path = path.lower().strip('/')

        if method not in self.method_handlers:
            self.method_handlers[method] = {}

        self.method_handlers[method][path] = handler


class APIHandler(BaseAPIHandler):
    def __init__(self, *args, **kwargs):
        super(APIHandler, self).__init__(*args, **kwargs)

        self.register_api('PUT', '/host/bootstrap', self.action_add_host)
        self.register_api('GET', '/host/check', self.action_check_host)
        self.register_api('GET', '/cachebrowse', self.action_get)

    @staticmethod
    def action_add_host(request):
        host = common.add_domain(request['host'])
        return{
            'result': 'success',
            'host': host
        }

    @staticmethod
    def action_check_host(request):
        is_active = common.is_host_active(request['host'])

        return {
            'result': 'active' if is_active else 'inactive',
            'host': request['host']
        }

    @staticmethod
    def action_get(request):
        keys = ['url', 'target', 'method', 'scheme', 'port']
        kwargs = {k: request[k] for k in keys if k in request}
        response = http.request(**kwargs)

        if request.get('json', False):
            response_message = {
                'status': response.status,
                'reason': response.reason
            }
            if request.get('headers', True):
                response_message['headers'] = {k: v for (k, v) in response.getheaders()}
            if request.get('raw', False):
                response_message['raw'] = response.read(raw=True)
            elif request.get('body', True):
                response_message['body'] = response.read()
            return response_message
        else:
            if request.get('raw', False):
                return response.get_raw(), ResponseOptions(send_json=False)
            else:
                return response.body, ResponseOptions(send_json=False)
