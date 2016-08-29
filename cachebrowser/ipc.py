import json

from websocket_server import WebsocketServer

from cachebrowser.api.core import api_manager, APIRequest


class IPCManager(object):
    def __init__(self, settings):
        self.settings = settings

        self.websocket_server = IPCWebSocket(self, settings.ipc_port)
        self.websocket_server.start()

        self.subscribtions = {}

        api_manager.register_api('/subscribe', self.on_subscribe)
        api_manager.register_api('/unsubscribe', self.on_unsubscribe)

    def publish(self, channel, message):
        mes = {
            'channel': channel,
            'data': message,
            'message_type': 'publish'
        }
        self.websocket_server.broadcast(mes)

    def on_message(self, client, message):
        route = message['route']
        params = message.get('params', {})
        req_id = message['request_id']

        request = IPCRequest(req_id, self, client, route, params)
        api_manager.handle_api_request(request)

    def send_response(self, request, response):
        self.websocket_server.send(request.client, {
            'message_type': 'response',
            'request_id': request.id,
            'response': response
        })

    def on_subscribe(self, request):
        # TODO Manage subcription to avoid redundant publishing
        pass

    def on_unsubscribe(self, request):
        pass


class IPCWebSocket(object):
    def __init__(self, ipc, port):
        self.ipc = ipc
        self.server = WebsocketServer(port)
        self._set_callbacks(self.server)

        self.clients = []

    def start(self):
        from threading import Thread

        def run():
            self.server.run_forever()
        t = Thread(target=run)
        t.daemon = True
        t.start()

    def _set_callbacks(self, server):
        server.set_fn_new_client(self.on_connect)
        server.set_fn_client_left(self.on_disconnect)
        server.set_fn_message_received(self.on_message)

    def on_connect(self, client, server):
        self.clients.append(client)

    def on_disconnect(self, client, server):
        self.clients = [c for c in self.clients if c['id'] != client['id']]

    def on_message(self, client, server, message):
        message = json.loads(message)
        self.ipc.on_message(client, message)

    def broadcast(self, message):
        message = json.dumps(message)
        for c in self.clients:
            self.server.send_message(c, message)

    def send(self, client, message):
        self.server.send_message(client, json.dumps(message))


class IPCRequest(APIRequest):
    def __init__(self, request_id, ipc, client, route, params):
        self.id = request_id
        self.ipc = ipc
        self.client = client

        super(IPCRequest, self).__init__(route, params)

    def reply(self, response=None):
        self.ipc.send_response(self, response)
