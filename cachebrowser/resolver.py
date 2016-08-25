from cachebrowser.bootstrap import BootstrapError
from netlib.tcp import Address

from cachebrowser.models import Host, DoesNotExist, CDN
from cachebrowser.proxy import FlowPipe

"""
If the client initiates an HTTP connection, the 'request' hook will be called first and then 'serverconnect'.
We can only upgrade the connection to HTTPS in 'request' hook using:
    flow.request.scheme = 'https'
    flow.request.port = 443
So, for this case we should check the host in the 'request' hook and see whether it should be upgraded.
If so we will change the scheme as shown above. If the request is already HTTPS we won't do anything in 'request'.

In the 'serverconnect' hook we will then check whether the connection address and sni has to be changed.

This is bad a little because for every HTTP request we will have to lookup the Host from the database twice. But so be
it for now.
"""


class Resolver(FlowPipe):
    def __init__(self, bootstrapper, *args, **kwargs):
        super(Resolver, self).__init__(*args, **kwargs)
        self.bootstrapper = bootstrapper

    def start(self):
        self._id_counter = 1

    def serverconnect(self, server_conn):
        hostname = server_conn.address.host

        # TODO (NOT FOR ALL SITE, BUT NEEDED FOR YOUTUBE)
        server_conn.sni = ''

        server_conn.cachebrowsed = False
        server_conn.cdn = None
        server_conn.cb_status_message = ''

        try:
            host = Host.get_or_bootstrap(hostname=hostname)
        except DoesNotExist:
            err = "Bootstrapping host {} failed".format(hostname)
            server_conn.cb_status_message = err
            return server_conn

        # Skip if host is not active
        if not host.is_active:
            server_conn.status = "Host not active"
            return server_conn

        cdn = host.cdn
        if not cdn.valid or not cdn.edge_server:
            err = "Host {} does not have a valid CDN".format(hostname)
            server_conn.cb_status_message = err
            return server_conn

        server_conn.address = Address((cdn.edge_server, server_conn.address.port))
        server_conn.sni = ''

        server_conn.cachebrowsed = True
        server_conn.cdn = {'id': cdn.id, 'name': cdn.name}

        return server_conn

    def request(self, flow):
        flow._id = self._id_counter
        self._id_counter += 1

        flow.request.scheme_upgraded = False

        flow.request.headers['host'] = flow.request.pretty_host

        if flow.request.scheme == 'http':
            try:
                host = Host.get_or_bootstrap(hostname=flow.request.host)

                if host.is_active and host.ssl:
                    flow.request.scheme = 'https'
                    flow.request.port = 443

                    flow.request.scheme_upgraded = True

            except DoesNotExist:
                pass

        self.publish_flow(flow)
        return flow

    def response(self, flow):
        self.publish_flow(flow)

    def _get_or_bootstrap_host(self, hostname):
        try:
            return Host.get(Host.hostname == hostname)
        except DoesNotExist:
            try:
                host_data = self.bootstrapper.lookup_host(hostname)
            except BootstrapError:
                raise DoesNotExist

            host = Host(**host_data)

            try:
                host.cdn = CDN.get_or_bootstrap(host.cdn_id)
            except DoesNotExist:
                host.cdn = CDN.create(id=host.cdn_id, valid=False)

            host.save(force_insert=True)

            return host

    def _get_or_bootstrap_cdn(self, cdn_id):
        try:
            return CDN.get(CDN.id == cdn_id)
        except DoesNotExist:
            try:
                cdn_data = self.bootstrapper.lookup_cdn(id)
                cdn = CDN(**cdn_data)
                cdn.save(force_insert=True)
                return cdn
            except BootstrapError:
                raise DoesNotExist

    def publish_flow(self, flow):
        from util import get_flow_size
        log = {
            'id': flow._id,
            'url': flow.request.pretty_url,
            'method': flow.request.method,
            'scheme': flow.request.scheme,
            'scheme_upgraded': flow.request.scheme_upgraded,
            'request_size': get_flow_size(flow)[0],
            'request_headers': dict(flow.request.headers)
        }

        if flow.response is not None:
            log['status_code'] = flow.response.status_code
            log['reason'] = flow.response.reason
            log['response_size'] = get_flow_size(flow)[1]
            log['response_headers'] = dict(flow.response.headers)

        if getattr(flow.server_conn, 'cachebrowsed', None) is not None:
            log.update({
                'address': flow.server_conn.peer_address.host,
                'sni': flow.server_conn.sni,
                'cdn': flow.server_conn.cdn,
                'cachebrowsed': flow.server_conn.cachebrowsed,
                'cb_error': flow.server_conn.cb_status_message
            })

        self.publish('request-log', log)

# TODO publish error
