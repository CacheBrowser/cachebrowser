import logging

import mitmproxy.controller
import mitmproxy.proxy
import mitmproxy.flow
import mitmproxy.dump
import mitmproxy.cmdline
import mitmproxy.models
import mitmproxy.protocol
import mitmproxy as mproxy
from mitmproxy.script import script
from cachebrowser.models import Website
from cachebrowser.pipes import SKIP_PIPES

logger = logging.getLogger(__name__)


class TlsLayer(mproxy.protocol.TlsLayer):
    @property
    def sni_for_server_connection(self):
        if self.server_conn.sni is not None:
            return self.server_conn.sni
        return mproxy.protocol.TlsLayer.sni_for_server_connection.fget(self)


class ProxyConfig(mitmproxy.proxy.ProxyConfig):
    def __init__(self, context):
        mitmproxy.proxy.ProxyConfig.__init__(self, port=context.settings.port)

        self.context = context
        self.check_ignore = self._check_ignore

    def _check_ignore(self, address):
        """
        Have mitmproxy ignore connections for websites which are not enabled.
        This makes mitmproxy use the original certificate and just pass the data through.
        However we should still stop the pipes from processing the request (using WebsiteFilterPipe)
        """
        return False

        # if address is None:
        #     return False
        #
        # hostname = address[0] if type(address) == tuple else address.host
        # website, _ = Website.get_or_create(hostname=hostname)
        # return not website.enabled


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

    def _run_single_script_hook(self, script_obj, name, *args, **kwargs):
        if script_obj and not self.pause_scripts:
            try:
                return script_obj.run(name, *args, **kwargs)
            except script.ScriptException as e:
                self.add_event("Script error:\n" + str(e), "error")

    def run_script_hook(self, name, *args, **kwargs):
        for script_obj in self.scripts:
            result = self._run_single_script_hook(script_obj, name, *args, **kwargs)
            if result == SKIP_PIPES:
                break


class DumpProxyController(mitmproxy.dump.DumpMaster):
    def __init__(self, server):
        parser = mitmproxy.cmdline.mitmdump()
        options = parser.parse_args(None)
        dump_options = mitmproxy.dump.Options(**mitmproxy.cmdline.get_common_options(options))
        mitmproxy.dump.DumpMaster.__init__(self, server, dump_options)

    def add_pipe(self, pipe):
        pipe.set_master(self)
        self.scripts.append(pipe)
