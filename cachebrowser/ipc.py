import json
from threading import Thread
import traceback
import uuid
import logging

import tornado.ioloop
import tornado.web
import tornado.websocket

from cachebrowser.api.core import api_manager, APIRequest

logger = logging.getLogger(__name__)


class IPCRouter(object):
    def __init__(self):
        self.clients = {}
        self.channels = {}
        self.rpc_clients = {}
        self.rpc_pending_requests = {}

    def add_client(self, client_id, client):
        self.clients[client_id] = client

    def remove_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]

    def publish(self, channel, message):
        if channel not in self.channels:
            return

        dangling_clients = []

        for client_id in self.channels[channel]:
            if client_id not in self.clients:
                dangling_clients.append(client_id)
            else:
                self.clients[client_id].send_publish(channel, message)

        for client_id in dangling_clients:
            self.channels[channel].remove(client_id)

    def subscribe(self, client_id, channel):
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(client_id)

    def unsubscribe(self, client_id, channel):
        if channel in self.channels and client_id in self.channels[channel]:
            self.channels[channel].remove(client_id)

    def rpc_request(self, client_id, request_id, method, params):
        if method not in self.rpc_clients:
            # TODO Give error
            pass

        self.rpc_pending_requests[request_id] = client_id
        target_client_id = self.rpc_clients.get(method, None)
        if target_client_id is not None:
            client = self.clients.get(target_client_id, None)
            if client is not None:
                client.send_rpc_request(request_id, method, params)

        # TODO give error if route doesn't exist

    def rpc_response(self, request_id, response):
        client_id = self.rpc_pending_requests.pop(request_id)
        client = self.clients.get(client_id, None)
        if client is not None:
            client.send_rpc_response(request_id, response)

    def register_rpc(self, client_id, method):
        # TODO give error if already registered
        self.rpc_clients[method] = client_id


class IPCClient(object):
    """
        General rule: these methods shouldn't need to interact with the router. They are called from the router
    """
    def send_publish(self, channel, message):
        pass

    def send_rpc_request(self, request_id, method, params):
        pass

    def send_rpc_response(self, request_id, response):
        pass


class IPCManager(IPCClient):
    def __init__(self, context):
        self.context = context

        self.router = IPCRouter()

        self.id = 'local_client'
        self.router.add_client(self.id, self)

        self.websocket = self.initialize_websocket_server(context.settings.ipc_port)

    def initialize_websocket_server(self, port):
        app = tornado.web.Application([
            (r'/', WebSocketIPCClient, {'router': self.router}),
        ])

        def run_loop():
            logger.debug("Starting IPC websocket server on port {}".format(port))
            ioloop = tornado.ioloop.IOLoop()
            ioloop.make_current()
            app.listen(port)
            ioloop.start()

        t = Thread(target=run_loop)
        t.daemon = True
        t.start()

        return app

    def publish(self, channel, message):
        self.router.publish(channel, message)

    def subscribe(self, channel, callback):
        raise NotImplementedError("Local subscriptions not implemented")

    def register_rpc(self, method, handler):
        logger.debug("Registering RPC method {}".format(method))
        self.router.register_rpc(self.id, method)

    def register_rpc_handlers(self, routes):
        for route in routes:
            self.register_rpc(route[0], route[1])

    def send_publish(self, channel, message):
        raise NotImplementedError("Local subscriptions not implemented")

    def send_rpc_request(self, request_id, method, params):
        request = RPCRequest(self.router, request_id, method, params)
        api_manager.handle_api_request(self.context, request)

    def send_rpc_response(self, request_id, response):
        raise NotImplementedError()


class RPCRequest(APIRequest):
    def __init__(self, router, request_id, route, params):
        self.id = request_id
        self.router = router

        super(RPCRequest, self).__init__(route, params)

    def reply(self, response=None):
        self.router.rpc_response(self.id, response)


class WebSocketIPCClient(tornado.websocket.WebSocketHandler, IPCClient):
    def initialize(self, router=None):
        self.id = str(uuid.uuid4())[:8]
        self.router = router

    def open(self, *args, **kwargs):
        self.router.add_client(self.id, self)

    def on_close(self):
        self.router.remove_client(self.id)

    def on_message(self, message):
        try:
            json_message = json.loads(message)
        except ValueError:
            logger.error("IPC: received invalid json message:\n{}".format(message))
        else:
            self.handle_message(json_message)

    def handle_message(self, message):
        message_type = message.get('type', None)

        if message_type is None:
            logger.error("IPC: received message with no type")

        try:
            if message_type == 'pub':
                self.router.publish(message['channel'], message['message'])
            elif message_type == 'sub':
                self.router.subscribe(self.id, message['channel'])
            elif message_type == 'unsub':
                self.router.unsubscribe(self.id, message['channel'])
            elif message_type == 'rpc_req':
                self.router.rpc_request(self.id, message['request_id'], message['method'], message.get('params', {}))
        except Exception as e:
            logger.error("Uncaught exception occurred while handling IPC message: {}".format(message))
            traceback.print_exc()

    def send_publish(self, channel, message):
        self.send({
            'type': 'pub',
            'channel': channel,
            'message': message
        })

    def send_rpc_request(self, request_id, method, params):
        self.send({
            'type': 'rpc_req',
            'request_id': request_id,
            'method': method,
            'params': params
        })

    def send_rpc_response(self, request_id, response):
        self.send({
            'type': 'rpc_resp',
            'request_id': request_id,
            'message': response
        })

    def send(self, message):
        self.write_message(message)

    def check_origin(self, origin):
        return True
