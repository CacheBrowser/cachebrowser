import json
from core import common


def action_add_domain(connection, message):
    common.add_domain(message['data']['domain'])
    connection.send(json.dumps({
        'result': 'success',
        'domain': message['data']['domain']
    }))
    connection.send('\n')


def handle_message(connection, message):
    print(json.dumps(message))
    handler = {
        'add domain': action_add_domain
    }.get(message['action'], None)

    if handler:
        return handler(connection, message)

    connection.send(json.dumps({
        'error': 'Unrecognized action'
    }))