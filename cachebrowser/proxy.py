import mitmproxy.controller
import mitmproxy.flow
import mitmproxy.dump
import mitmproxy.cmdline
import mitmproxy.models
import mitmproxy.protocol
import mitmproxy as mproxy
from mitmproxy.script import Script
from mitmproxy.script.script_context import ScriptContext

from six import StringIO
from cachebrowser.ipc import IPCManager


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


#
# class ServerConnection(mproxy.models.ServerConnection):
#     def __init__(self, *args, **kwargs):
#         mproxy.models.ServerConnection.__init__(self, *args, **kwargs)
#
#         self.is_fake = False
#
#     def fake_it(self):
#         self.is_fake = True
#         self.connect = self._fake_connect
#         self.establish_ssl = self._fake_establish_ssl
#         self.finish = self._fake_finish
#
#     def _fake_connect(self):
#         print("Fake Connect called")
#         self.wfile = StringIO()
#         self.rfile = StringIO()
#
#     def _fake_establish_ssl(self, clientcerts, sni, **kwargs):
#         print("Fake SSL")
#
#     def _fake_finish(self):
#         print("Finish")


class TlsLayer(mproxy.protocol.TlsLayer):
    @property
    def sni_for_server_connection(self):
        if self.server_conn.sni is not None:
            return self.server_conn.sni
        return mproxy.protocol.TlsLayer.sni_for_server_connection.fget(self)


class ProxyController(mitmproxy.flow.FlowMaster):
    def __init__(self, server, state=None):
        from log import ProxyLogger

        if state is None:
            state = mitmproxy.flow.State()

        mitmproxy.flow.FlowMaster.__init__(self, server, state)

        self.logger = ProxyLogger('warning')

        self.ipc = IPCManager()

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
        self.logger.log(e, level, key)

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

        # class ProxyController(mitmproxy.controller.Master):
        # class ProxyController(mitmproxy.flow.FlowMaster):
        #     def __init__(self, server):
        #         # mitmproxy.controller.Master.__init__(self, server)
        #         mitmproxy.flow.FlowMaster.__init__(self, server, mitmproxy.flow.State())
        #
        #         # self.context = ScriptContext(self)
        #         # self.scripts.append(ProxyScript(self))
        #
        #     def add_pipe(self, pipe):
        #         self.scripts.append(pipe)

        # def handle_clientconnect(self, root_layer):
        #     root_layer.reply()
        #
        # def handle_clientdisconnect(self, root_layer):
        #     root_layer.reply()

        # def serverconnect(self, server_conn):
        #     if server_conn.sni:
        #         print("[{}] [Connect] {}  SNI: {}".format(server_conn.id, server_conn.address, server_conn.sni))
        #     else:
        #         sid = hex(id(server_conn))[4:]
        #         print("[{}] [Connect] {}".format(kcolor(sid), server_conn.address))

        # for pipe in self.pipeline:
        #     print(pipe)
        #     if not pipe.handle_serverconnect(server_conn):
        #         break

        # server_conn.reply(Kill)
        # server_conn.reply()

        # def handle_serverdisconnect(self, server_conn):
        #     server_conn.reply()

        # def request(self, flow):
        #     # self.replay_request(flow, True, True)
        #     # f = self.context.duplicate_flow(flow)
        #     # f.request.path = "/changed"
        #     # self.context.replay_request(f)
        #
        #     sid = hex(id(flow.server_conn))[4:]
        #     print("[{}] [{}] {}".format(kcolor(sid), flow.request.method, flow.request.url))
        #     # flow.reply()


        # def handle_response(self, flow):
        #     flow.reply()
        #
        # def handle_next_layer(self, top_layer):
        #     top_layer.reply()
        #
        # def handle_error(self, f):
        #     f.reply()
        #     return f

        # def run_script_hook(self, name, *args, **kwargs):
        #     if self.pause_scripts:
        #         return
        #     hook = getattr(self, name, None)
        #     if hook:
        #         hook(*args, **kwargs)
