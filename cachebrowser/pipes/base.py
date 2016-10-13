from mitmproxy.script import Script, ScriptContext


class FlowPipe(Script, ScriptContext):
    def __init__(self, context, master=None):
        self.context = context
        self.bootstrapper = self.context.bootstrapper
        self.settings = self.context.settings

        self.enabled = True

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
        if not self.enabled:
            return

        hook = getattr(self, name, None)
        if hook:
            return hook(*args, **kwargs)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

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