import logging
import http
import shlex
import re
from network import ConnectionHandler
from models import Host, CDN

import common


class BaseCLIHandler(ConnectionHandler):
    def __init__(self, *args, **kwargs):
        super(BaseCLIHandler, self).__init__(*args, **kwargs)
        self._handlers = {}

    @common.silent_fail(log=True)
    def on_data(self, data, *kwargs):
        if data is None or len(data.strip()) == 0:
            return
        message = data.strip()
        parts = shlex.split(message)
        args = []
        kwargs = {}
        for part in parts:
            match = re.match('(.*)=(.*)', part)
            if match:
                kwargs[match.group(1)] = match.group(2)
            else:
                args.append(part)

        self.handle_command(*args, **kwargs)

    def on_connect(self):
        logging.debug("New CLI connection established with %s" % str(self.address))

    def handle_command(self, *args, **kwargs):
        try:
            self._handle_command(*args, **kwargs)
        except UnrecognizedCommandException as e:
            self.send_line("Unrecognized command '" + e.command.strip() + "'.")
            if e.valid_commands:
                self.send_line(" Valid commands are:\n%s\n" % (', '.join(e.valid_commands)))
        except InsufficientCommandParametersException as e:
            self.send_line("Expected %s parameter\n" % e.param)

    def _handle_command(self, *parts, **kwargs):
        valid_commands = self._handlers
        for i in range(len(parts)):
            command = parts[i]
            if command == '?':
                return self.send_line("%s\n" % (', '.join(valid_commands.keys())))
            if command not in valid_commands:
                if '_' in valid_commands:
                    return valid_commands['_'](*parts[i:], **kwargs)
                else:
                    raise UnrecognizedCommandException(command, valid_commands.keys())

            valid_commands = valid_commands[command]
            if hasattr(valid_commands, '__call__'):
                return valid_commands(*parts[i + 1:], **kwargs)

        if hasattr(valid_commands, '__call__'):
            return valid_commands(**kwargs)
        if '_' in valid_commands:
            return valid_commands['_'](**kwargs)
        raise UnrecognizedCommandException('', [])

    def send_line(self, message):
        self.send(message + '\n')

    def register_command(self, command, handler):
        parts = command.split()
        handlers = self._handlers
        for part in parts[:-1]:
            if part not in handlers:
                handlers[part] = {}
            handlers = handlers[part]
        handlers[parts[-1]] = handler


class CLIHandler(BaseCLIHandler):
    def __init__(self, *args, **kwargs):
        super(CLIHandler, self).__init__(*args, **kwargs)

        self.register_command('bootstrap', self.domain_add)
        self.register_command('list hosts', self.domain_list)
        self.register_command('list cdn', self.cdn_list)
        self.register_command('get', self.make_request)

    def domain_add(self, host=None):
        """
        Activate a host with CacheBrowser
        """
        if not host:
            raise InsufficientCommandParametersException('host')

        result_host = common.add_domain(host)
        if result_host:
            self.send_line("Host '%s' activated" % result_host)
        else:
            self.send_line("Host '%s' could not be activated, see logs for more information" % host)

    def domain_list(self):
        """
        List the active hosts
        """
        hosts = Host.select()
        for host in hosts:
            self.send_line("%*s: %s" % (20, host.url, host.cdn.id))

    def cdn_list(self):
        """
        List CDNs registered with CacheBrowser
        """
        cdns = CDN.select()
        for cdn in cdns:
            self.send_line("%*s:  %s" % (15, cdn.id, ' '.join(cdn.addresses)))

    def make_request(self, url, target=None, *args):
        """
        Make a http request using CacheBrowser
        """
        response = http.request(url, target=target)
        self.send_line(response.read())


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