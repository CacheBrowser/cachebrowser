import copy
import json
import logging
import http
import common


__all__ = ['handle_connection']


class BaseAPIHandler(object):
    def __init__(self, sock):
        self._socket = sock
        self._handlers = {}

    @common.silent_fail(log=True)
    def on_data(self, data, *kwargs):
        if data is None or len(data.strip()) == 0:
            return
        logging.debug(data)

        try:
            message = json.loads(data.strip())
        except ValueError:
            logging.error("Invalid JSON recevied: %s (%d)" % (data, len(data)))
            self.send_message({
                'error': 'Invalid message'
            })
            return

        handler = self._handlers.get(message['action'], None)

        if handler:
            def callback(response, send_json=True):
                if response is None:
                    return
                if send_json:
                    if 'messageId' in message:
                        response['messageId'] = message['messageId']
                    self.send_message(response)
                else:
                    self.send(response)
                self._socket.close()
            handler(message, callback)

            return

        self.send_message({
            'error': 'Unrecognized action'
        })

    def on_close(self):
        pass

    def send_message(self, message):
        self.send(json.dumps(message) + '\n')

    def send(self, data):
        self._socket.send(data)


class APIHandler(BaseAPIHandler):
    def __init__(self, *args, **kwargs):
        super(APIHandler, self).__init__(*args, **kwargs)
        self._handlers = {
            'add host': self.action_add_host,
            'check host': self.action_check_host,
            'get': self.get
        }

    def action_add_host(self, message, cb):
        host = common.add_domain(message['host'])
        cb({
            'result': 'success',
            'host': host
        })

    def action_check_host(self, message, cb):
        is_active = common.is_host_active(message['host'])

        cb({
            'result': 'active' if is_active else 'inactive',
            'host': message['host']
        })

    def get(self, message, cb):
        def callback(response):
            if message.get('json', False):
                response_message = {
                    'status': response.status,
                    'reason': response.reason
                }
                if message.get('headers', True):
                    response_message['headers'] = response.headers
                if message.get('raw', False):
                    response_message['raw'] = response.get_raw()
                if message.get('body', True):
                    response_message['body'] = response.body
                cb(response_message, send_json=True)
            else:
                if message.get('raw', False):
                    cb(response.get_raw(), send_json=False)
                else:
                    cb(response.body, send_json=False)

        keys = ['url', 'target', 'method', 'scheme', 'port']
        kwargs = {k: message[k] for k in keys if k in message}
        kwargs['callback'] = callback
        http.request(**kwargs)


def handle_connection(con, addr, looper):
    api_handler = APIHandler(con)
    logging.debug("New API connection established with %s" % str(addr))
    looper.register_socket(con, api_handler.on_data, api_handler.on_close)
