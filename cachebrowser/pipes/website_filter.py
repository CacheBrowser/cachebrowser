from urlparse import urlparse

from cachebrowser.models import Website
from cachebrowser.pipes.base import FlowPipe
from cachebrowser.pipes import SKIP_PIPES


class WebsiteFilterPipe(FlowPipe):
    def serverconnect(self, server_conn):
        if self._check_should_skip(server_conn=server_conn):
            return SKIP_PIPES

        hostname = server_conn.address.host
        website, _ = Website.get_or_create(hostname=hostname)

        if not website.enabled:
            return self._skip(server_conn=server_conn)

    def request(self, flow):
        if self._check_should_skip(flow=flow):
            return SKIP_PIPES

        hostname = urlparse(flow.request.url).netloc
        website, _ = Website.get_or_create(hostname=hostname)

        if not website.enabled:
            return self._skip(flow=flow)

    def response(self, flow):
        if self._check_should_skip(flow=flow):
            return SKIP_PIPES

        hostname = urlparse(flow.request.url).netloc
        website, _ = Website.get_or_create(hostname=hostname)

        if not website.enabled:
            return self._skip(flow=flow)

    def _check_should_skip(self, server_conn=None, flow=None):
        if server_conn is not None and hasattr(server_conn, '_skip_flow'):
            return True
        elif flow is not None:
            if hasattr(flow.server_conn, '_skip_flow') or hasattr(flow, '_skip_flow'):
                return True
        return False

    def _skip(self, server_conn=None, flow=None):
        if server_conn is not None:
            server_conn._skip_flow = True
        if flow is not None:
            flow._skip_flow = True

        return SKIP_PIPES