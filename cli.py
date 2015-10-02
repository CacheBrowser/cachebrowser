import logging

import common
import localdns


__all__ = ['handle_message']


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


def dummy_handler(*args):
    return


def get_next_handler(connection, command, command_list):
    if command == '?':
        connection.send("%s\n" % (', '.join(command_list)))
        return dummy_handler

    next_handler = command_list.get(command, None)

    if not next_handler:
        if '_' in command_list:
            return command_list['_']
        raise UnrecognizedCommandException(command, command_list)

    return next_handler


def domain_add(connection, domain, *rem):
    if not domain:
        raise InsufficientCommandParametersException('domain')

    common.add_domain(domain)


def dns_list(connection, *rem):
    records = localdns.list_records()
    connection.send('\n'.join(map(lambda (x, y): x + " " + y, records)))
    connection.send('\n\n')


def handle_domain_command(connection, command, *rem):
    get_next_handler(connection, command, {
        'add': domain_add
    })(connection, *rem)


def handle_dns_command(connection, command, *rem):
    get_next_handler(connection, command, {
        'list': dns_list
    })(connection, *rem)


def handle_command(connection, command, *rem):
    get_next_handler(connection, command, {
        'domain': handle_domain_command,
        'dns': handle_dns_command
    })(connection, *rem)


def handle_message(connection, message, *kwargs):
    if not message or len(message.strip()) == 0:
        return

    message = message.strip()

    parts = message.split(' ')

    try:
        handle_command(connection, *parts)
    except UnrecognizedCommandException as e:
        connection.send("Unrecognized command '" + e.command.strip() + "'.")
        if e.valid_commands:
            connection.send(" Valid commands are:\n%s\n" % (', '.join(e.valid_commands)))
    except InsufficientCommandParametersException as e:
        connection.send("Expected %s parameter\n" % e.param)


def handle_connection(connection, addr, looper):
    logging.debug("New CLI connection established with %s" % str(addr))
    looper.register_socket(connection, handle_message)