import logging

import mitmproxy.controller
import mitmproxy.flow
import mitmproxy.dump
import mitmproxy.cmdline
import mitmproxy.models
import mitmproxy.protocol
import mitmproxy as mproxy
from mitmproxy.script import Script
from mitmproxy.script.script_context import ScriptContext

logger = logging.getLogger(__name__)


class FlowPipe(Script, ScriptContext):
    def __init__(self, master=None):
        self._master = None
        if master:
            self.set_master(master)

    def set_master(self, master=None):
        self._master = master

    def log(self, message, level=None, key=None):
        self._master.add_event(message, level, key)

    def create_request(self, method, scheme, host, port, path):
        with self.pause():
            return self._master.create_request(method, scheme, host, port, path)

    def create_request_from_url(self, method, url, port=None):
        from six.moves.urllib.parse import urlparse
        u = urlparse(url)
        if port is None:
            port = 443 if u.scheme == 'https' else 80
        path = u.path
        if u.query:
            path = path + '?' + u.query
        return self.create_request(method, u.scheme, u.netloc, port, path)

    def send_request(self, flow, run_hooks=False, block=False):
        self._master.replay_request(flow, run_scripthooks=run_hooks, block=block)

    def run(self, name, *args, **kwargs):
        hook = getattr(self, name, None)
        if hook:
            hook(*args, **kwargs)

    def pause(self):
        _self = self

        class Pauser:
            def __enter__(self):
                _self._master.pause_scripts = True

            def __exit__(self, exc_type, exc_val, exc_tb):
                _self._master.pause_scripts = False

        return Pauser()

    def publish(self, *args, **kwargs):
        self._master.ipc.publish(*args, **kwargs)


class TlsLayer(mproxy.protocol.TlsLayer):
    @property
    def sni_for_server_connection(self):
        if self.server_conn.sni is not None:
            return self.server_conn.sni
        return mproxy.protocol.TlsLayer.sni_for_server_connection.fget(self)


class ProxyController(mitmproxy.flow.FlowMaster):
    def __init__(self, server, ipc, state=None):
        if state is None:
            state = mitmproxy.flow.State()

        mitmproxy.flow.FlowMaster.__init__(self, server, state)

        self.ipc = ipc

    def add_pipe(self, pipe):
        pipe.set_master(self)
        self.scripts.append(pipe)

    def handle_serverconnect(self, server_conn):
        # server_conn.__class__ = ServerConnection
        mproxy.flow.FlowMaster.handle_serverconnect(self, server_conn)

    def handle_request(self, f):
        mproxy.flow.FlowMaster.handle_request(self, f)
        if f and not (hasattr(f, 'should_reply') and f.should_reply is False):
            f.reply()
        return f

    def handle_response(self, f):
        mproxy.flow.FlowMaster.handle_response(self, f)
        if f:
            f.reply()
        return f

    def handle_error(self, f):
        mproxy.flow.FlowMaster.handle_error(self, f)
        return f

    def handle_next_layer(self, top_layer):
        if top_layer.__class__ == mproxy.protocol.TlsLayer:
            top_layer.__class__ = TlsLayer
        mproxy.flow.FlowMaster.handle_next_layer(self, top_layer)

    def add_event(self, e, level=None, key=None):
        # mitmproxy gives TLS error: Invalid Hostname because of not using SNI
        # ignore the message so the log doesn't get cluttered

        ignore_messages = [
            "TLS verification failed for upstream server at depth 0 with error: Invalid Hostname",
            "Ignoring server verification error, continuing with connection",
            "clientconnect",
            "clientdisconnect",
        ]

        if any([e.endswith(s) for s in ignore_messages]):
            return

        logger.log(getattr(logging, level.upper()), e)
        # logger.log(logging.DEBUG, e)

    def run(self):
        self.run_script_hook('start')
        super(ProxyController, self).run()


class DumpProxyController(mitmproxy.dump.DumpMaster):
    def __init__(self, server):
        parser = mitmproxy.cmdline.mitmdump()
        options = parser.parse_args(None)
        dump_options = mitmproxy.dump.Options(**mitmproxy.cmdline.get_common_options(options))
        mitmproxy.dump.DumpMaster.__init__(self, server, dump_options)

    def add_pipe(self, pipe):
        pipe.set_master(self)
        self.scripts.append(pipe)
