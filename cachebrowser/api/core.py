from cachebrowser.api.routes import routes


class APIRequest(object):
    def __init__(self, route, params):
        self.route = route
        self.params = params

    def reply(self, response):
        raise NotImplementedError()


class APIManager(object):
    def __init__(self):
        self.handlers = {}

    def register_api(self, route, handler):
        self.handlers[route] = handler

    def handle_api_request(self, request):
        self.handlers[request.route](request)


api_manager = APIManager()

for route in routes:
    api_manager.register_api(route[0], route[1])
