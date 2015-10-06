import logging

import common
import localdns

__all__ = ['handle_message']
connection = None

def domain_add(host=None):
    if not host:
        raise InsufficientCommandParametersException('host')

    common.add_domain(host)


_commands = {
    'add': {
        'host': domain_add
    }
}


def handle_command(*parts):
    valid_commands = _commands
    for i in range(len(parts)):
        command = parts[i]
        if command == '?':
            return connection.send("%s\n" % (', '.join(valid_commands.keys())))
        if command not in valid_commands:
            if '_' in valid_commands:
                return valid_commands['_'](*parts[i:])
            else:
                raise UnrecognizedCommandException(command, valid_commands.keys())

        valid_commands = valid_commands[command]
        if hasattr(valid_commands, '__call__'):
            return valid_commands(*parts[i + 1:])

    if hasattr(valid_commands, '__call__'):
        return valid_commands()
    if '_' in valid_commands:
        return valid_commands['_']()
    raise UnrecognizedCommandException('', [])


def handle_message(message, *kwargs):
    if not message or len(message.strip()) == 0:
        return

    message = message.strip()

    parts = message.split(' ')

    try:
        handle_command(*parts)
    except UnrecognizedCommandException as e:
        connection.send("Unrecognized command '" + e.command.strip() + "'.")
        if e.valid_commands:
            connection.send(" Valid commands are:\n%s\n" % (', '.join(e.valid_commands)))
    except InsufficientCommandParametersException as e:
        connection.send("Expected %s parameter\n" % e.param)


def handle_close():
    pass


def handle_connection(conn, addr, looper):
    global connection
    connection = conn
    logging.debug("New CLI connection established with %s" % str(addr))
    looper.register_socket(connection, handle_message, handle_close)


class UnrecognizedCommandException(Exception):
    def __init__(self, command, valid_commands=None):
        self.command = command
        if self.command:
            self.command = self.command.strip()
        self.valid_commands = valid_commands
        if self.valid_commands:
            self.valid_commands = list(map(lambda x: x.strip(), self.valid_commands))


class InsufficientCommandParametersException(Exception):
    def __init__(self, param):
        self.param = param
        if self.param:
            self.param = self.param.strip()