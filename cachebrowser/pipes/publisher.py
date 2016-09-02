from cachebrowser.pipes.base import FlowPipe
from cachebrowser.util import get_flow_size


class PublisherPipe(FlowPipe):
    def __init__(self, *args, **kwargs):
        super(PublisherPipe, self).__init__(*args, **kwargs)
        self._id_counter = 1

    def start(self):
        self._id_counter = 1

    def request(self, flow):
        flow._id = self._id_counter
        self._id_counter += 1

        self.publish_flow(flow)
        return flow

    def response(self, flow):
        self.publish_flow(flow)

    def publish_flow(self, flow):
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
