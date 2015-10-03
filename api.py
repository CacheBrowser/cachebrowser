import json
import logging

import common


__all__ = ['handle_connection']


def action_add_domain(message):
    common.add_domain(message['data']['domain'])
    connection.send(json.dumps({
        'result': 'success',
        'domain': message['data']['domain']
    }))
    connection.send('\n')


def handle_message(message, *kwargs):
    print(json.dumps(message))
    handler = {
        'add domain': action_add_domain
    }.get(message['action'], None)

    if handler:
        return handler(message)

    connection.send(json.dumps({
        'error': 'Unrecognized action'
    }))


def handle_data(data):
    handle_message(json.loads(data))


def handle_close():
    pass

connection = None
def handle_connection(con, addr, looper):
    global connection
    connection = con
    logging.debug("New API connection established with %s" % str(addr))
    looper.register_socket(connection, handle_data, handle_close)
