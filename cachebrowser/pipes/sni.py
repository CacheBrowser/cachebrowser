from cachebrowser.pipes.base import FlowPipe


SNI_EMPTY = "empty"
SNI_FRONT = "font"
SNI_ORIGINAL = "original"


class SNIPipe(FlowPipe):
    def serverconnect(self, server_conn):
        host, cdn = getattr(server_conn, 'host', None), getattr(server_conn, 'cdn', None)

        if host and host.sni_policy:
            self._apply_sni_policy(server_conn, host.sni_policy)
        elif cdn and cdn.sni_policy:
            self._apply_sni_policy(server_conn, cdn.sni_policy)
        else:
            self._apply_sni_policy(server_conn, self.settings.default_sni_policy)

        return server_conn

    @staticmethod
    def _apply_sni_policy(server_conn, sni_policy):
        server_conn.sni_policy = sni_policy

        if sni_policy == SNI_EMPTY:
            server_conn.sni = ''
        elif sni_policy == SNI_ORIGINAL:
            server_conn.sni = None
        elif sni_policy == SNI_FRONT:
            # TODO Implement Front
            pass
