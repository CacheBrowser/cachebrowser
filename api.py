import json
import logging

import common


__all__ = ['handle_connection']


class BaseAPIHandler(object):
    def __init__(self, sock):
        self._socket = sock
        self._handlers = {}

    @common.silent_fail(log=True)
    def on_data(self, data, *kwargs):
        if data is None or len(data.strip()) == 0:
            print("---")
            return
        print(data)

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
            response = handler(message)
            if response is not None:
                response['messageId'] = message['messageId']
            self.send_message(response)
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
            'check host': self.action_check_host
        }

    def action_add_host(self, message):
        host = common.add_domain(message['host'])
        return {
            'result': 'success',
            'host': host
        }

    def action_check_host(self, message):
        is_active = common.is_host_active(message['host'])

        return {
            'result': 'active' if is_active else 'inactive',
            'host': message['host']
        }


def handle_connection(con, addr, looper):
    api_handler = APIHandler(con)
    logging.debug("New API connection established with %s" % str(addr))
    looper.register_socket(con, api_handler.on_data, api_handler.on_close)
