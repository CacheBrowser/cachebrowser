import json
import logging

import common


__all__ = ['handle_connection']


def action_add_domain(connection, message):
    common.add_domain(message['data']['domain'])
    connection.send(json.dumps({
        'result': 'success',
        'domain': message['data']['domain']
    }))
    connection.send('\n')


def handle_message(connection, message, *kwargs):
    print(json.dumps(message))
    handler = {
        'add domain': action_add_domain
    }.get(message['action'], None)

    if handler:
        return handler(connection, message)

    connection.send(json.dumps({
        'error': 'Unrecognized action'
    }))


def handle_data(connection, data):
    handle_message(connection, json.loads(data))


def handle_connection(connection, addr, looper):
    logging.debug("New API connection established with %s" % str(addr))
    looper.register_socket(connection, handle_data)
