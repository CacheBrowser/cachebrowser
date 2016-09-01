from cachebrowser.api.routes import routes


class APIRequest(object):
    def __init__(self, route, params):
        self.route = route
        self.params = params

    def reply(self, response):
        raise NotImplementedError()


class BaseAPIManager(object):
    def __init__(self):
        self.handlers = {}

    def register_api(self, route, handler):
        self.handlers[route] = handler

    def handle_api_request(self, context, request):
        self.handlers[request.route](context, request)


class APIManager(BaseAPIManager):
    def __init__(self):
        super(APIManager, self).__init__()

        for route in routes:
            self.register_api(route[0], route[1])
        
api_manager = APIManager()

