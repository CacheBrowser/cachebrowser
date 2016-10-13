# cdn.jsdelivr.net
import logging
from time import time, sleep
from threading import Thread, RLock
from random import random, shuffle, choice
from six.moves.urllib.parse import urlparse

from mitmproxy.models import HTTPResponse
from netlib.http import Headers

from cachebrowser.pipes.base import FlowPipe
from cachebrowser.util import get_flow_size, pretty_bytes


logger = logging.getLogger(__name__)

DOWNSTREAM_STD = 100000


def should_i(prob):
    return random() < prob


class ScramblerPipe(FlowPipe):
    PROB_AD_BLOCK = 1.0
    PROB_AD_DECOY = 1.0
    PROB_DECOY = 0.2

    OVERHEAD = 0.1
    BLOCK_ADS = True

    def __init__(self, *args, **kwargs):
        super(ScramblerPipe, self).__init__(*args, **kwargs)

        self.overhead = self.OVERHEAD
        self.drop_ads = True
        self.send_decoys = True
        self.org_names = self.read_org_names()


        self.adblocker = AdBlocker()
        self.netstats = NetStatKeeper(self.org_names)
        self.decoymaker = DecoyMaker(self.netstats, self.org_names)

        self.api = ScramblerAPI(self.context, self)

        self.block_count = 0
        self.notblock_count = 0

        self.upstream_overhead = 0
        self.upstream_traffic = 0       # Non-Overhead traffic
        self.downstream_overhead = 0
        self.downstream_traffic = 0
        self.decoysent = 0
        self.decoyreceived = 0

        self.user_requests = 0
        self.blocked_requests = 0

    def start(self):
        # super(Scrambler, self).start()
        self.adblocker.load_blacklist(self.context.settings.data_path('scrambler/ad-domains'),
                                      self.context.settings.data_path('scrambler/blacklist'))
        self.decoymaker.load_decoys(self.context.settings.data_path('scrambler/decoy.json'))

    def reset(self):
        self.block_count = 0
        self.notblock_count = 0
        self.netstats.reset()

        self.upstream_overhead = 0
        self.upstream_traffic = 0       # Non-Overhead traffic
        self.downstream_overhead = 0
        self.downstream_traffic = 0
        self.decoysent = 0
        self.decoyreceived = 0
        self.decoymaker.inflight = 0

        self.user_requests = 0
        self.blocked_requests = 0

    def get_stats(self):
        return {
            'blocked': 0,
            'upstream_overhead': self.upstream_overhead,
            'upstream_normal': self.upstream_traffic,
            'downstream_overhead': self.downstream_overhead,
            'downstream_normal': self.downstream_traffic,
            'decoys': self.decoyreceived,
            'decoys_sent': self.decoysent,
            'max_overhead': self.overhead,
            'user_requests': self.user_requests,
            'blocked_requests': self.blocked_requests,
            'adblock_enabled': self.BLOCK_ADS
        }

    def serverconnect(self, server_conn):
        pass

    def print_stats(self):
        print(self.decoymaker.inflight)
        print("Sent: {}  Received: {}  Overhead: {}  Traffic: {}   Overhead: {}  Traffic: {} ".format(self.decoysent, self.decoyreceived,
                                                                         pretty_bytes(self.downstream_overhead), pretty_bytes(self.downstream_traffic),
                                                                          pretty_bytes(self.upstream_overhead), pretty_bytes(self.upstream_traffic)))

    def request(self, flow):
        is_decoy = hasattr(flow, 'is_decoy') and flow.is_decoy

        if is_decoy:
            self.netstats.update_real_upstream(flow)
            self.upstream_overhead += get_flow_size(flow)[0]

            self.decoysent += 1
        else:
            self.netstats.update_real_upstream(flow)
            self.netstats.update_requested_upstream(flow)
            self.upstream_traffic += get_flow_size(flow)[0]

            self.user_requests += 1

            if self.BLOCK_ADS and self.adblocker.should_block(flow):
                self.blocked_requests += 1
                self.dummy_response(flow)
                self._send_decoy_request(skip_netname=_whois(flow, self.org_names))
            else:
                for i in range(6):
                    wanted = sum(self.netstats.requested_downstream_traffic.values())
                    actual = sum(self.netstats.real_downstream_traffic.values())
                    if actual + self.decoymaker.inflight < wanted + wanted * self.overhead:
                        self._send_decoy_request()

        # self.print_stats()
        # print("")
        # logging.info('>> {}  {} '.format(self.notblock_count, self.block_count))

    def response(self, flow):
        is_decoy = hasattr(flow, 'is_decoy') and flow.is_decoy

        if is_decoy:
            self.netstats.update_real_downstream(flow)
            self.decoymaker.record_decoy_received(flow)
            self.decoyreceived += 1

            self.downstream_overhead += get_flow_size(flow)[1]
        else:
            self.netstats.update_real_downstream(flow)
            self.netstats.update_requested_downstream(flow)
            self.downstream_traffic += get_flow_size(flow)[1]

    def read_org_names(self):
        with open(self.context.settings.data_path('scrambler/decoy.json')) as f:
            import json
            netname_data = json.loads(f.read())
            org_names = netname_data.keys()
        org_names.append('OTHER')
        return org_names

    def _send_decoy_request(self, skip_netname=None):
        decoyurl = self.decoymaker.get_decoy_url(skip_netname)
        # logging.info("Sending DECOY to {}".format(decoyurl))
        if decoyurl is not None:
            new_flow = self.create_request_from_url('GET', decoyurl)

            # Don't update stats on dummy request
            new_flow.outgoing_request = True
            new_flow.is_decoy = True
            self.send_request(new_flow, run_hooks=True)

            self.decoymaker.record_decoy_sent(new_flow, decoyurl)

    def handle_ads(self, flow):
        domain = urlparse(flow.request.url).netloc

        if self.adblocker.should_block(flow) and self.drop_ads and should_i(self.PROB_AD_BLOCK):
            self.dummy_response(flow)

            if self.send_decoys and should_i(self.PROB_AD_DECOY):
                decoy_url = self.decoymaker.get_decoy_url(flow)
                if decoy_url is not None:
                    # logging.info("@@@@@@@@@@@@@@  Sending Decoy Request {}".format(decoy_url))
                    new_flow = self.create_request_from_url('GET', decoy_url)

                    # Don't update stats on dummy request
                    new_flow.outgoing_request = True
                    new_flow.is_dummy = True
                    self.send_request(new_flow, run_hooks=True)

            return True

        return False

    def dummy_response(self, flow):
        resp = HTTPResponse(
            "HTTP/1.1", 444, "Blocked",
            Headers(Content_Type="text/html"),
            "You got blocked by CDNReaper")
        flow.reply(resp)

    def error(self, flow):
        pass


class ScramblerAPI(object):
    def __init__(self, context, scrambler):
        self.scrambler = scrambler

        context.ipc.register_rpc('/scrambler/get/settings', self.get_settings)
        context.ipc.register_rpc('/scrambler/set/settings', self.set_settings)
        context.ipc.register_rpc('/scrambler/enable', self.enable_scrambler)
        context.ipc.register_rpc('/scrambler/disable', self.disable_scrambler)

    def get_settings(self, context, request):
        request.reply({
            'result': 'success',
            'settings': {
                'enabled': self.scrambler.enabled,
                'overhead': self.scrambler.overhead,
                'drops': self.scrambler.drop_ads,
                'decoys': self.scrambler.send_decoys
            }
        })

    def set_settings(self, context, request):
        if 'enabled' in request.params:
            self.scrambler.enabled = bool(request.params['enabled'])
        if 'overhead' in request.params:
            self.scrambler.overhead = int(request.params['overhead'])
        if 'drops' in request.params:
            self.scrambler.drop_ads = bool(request.params['drops'])
        if 'decoys' in request.params:
            self.scrambler.send_decoys = bool(request.params['decoys'])
        request.reply({
            'result': 'success'
        })

    def enable_scrambler(self, context, request):
        self.scrambler.enable()
        request.reply({'result': 'success'})

    def disable_scrambler(self, context, request):
        self.scrambler.disable()
        request.reply({'result': 'success'})


class NetStatKeeper(object):
    UPSTREAM_STD = 200
    DOWNSTREAM_STD = DOWNSTREAM_STD

    S = 10

    def __init__(self, org_names):
        from collections import deque
        self.org_names = org_names

        self.requested_upstream = {}
        self.requested_downstream = {}
        self.requested_upstream_traffic = {}
        self.requested_downstream_traffic = {}

        self.real_upstream = {}
        self.real_downstream = {}
        self.real_upstream_traffic = {}
        self.real_downstream_traffic = {}

        self.lock = RLock()
        # self.outgoing_lock = RLock()

        for org in org_names:
            self.requested_upstream[org] = deque()
            self.requested_downstream[org] = deque()
            self.real_downstream[org] = deque()
            self.real_upstream[org] = deque()
            self.real_downstream_traffic[org] = 0
            self.real_upstream_traffic[org] = 0
            self.requested_downstream_traffic[org] = 0
            self.requested_upstream_traffic[org] = 0

        def refresher():
            def refresh(ds):
                for k in ds:
                    while len(ds[k]):
                        if ds[k][0][0] < threshold:
                            ds[k].popleft()
                        else:
                            break

            while True:
                sleep(1)
                now = time()
                threshold = now - self.S

                with self.lock:
                    refresh(self.requested_downstream)
                    refresh(self.requested_upstream)
                    refresh(self.real_downstream)
                    refresh(self.real_upstream)

                    for netname in org_names:
                        self.requested_upstream_traffic[netname] = 0
                        for item in self.requested_upstream[netname]:
                            self.requested_upstream_traffic[netname] += item[1]

                        self.requested_downstream_traffic[netname] = 0
                        for item in self.requested_downstream[netname]:
                            self.requested_downstream_traffic[netname] += item[1]

                        self.real_upstream_traffic[netname] = 0
                        for item in self.real_upstream[netname]:
                            self.real_upstream_traffic[netname] += item[1]

                        self.real_downstream_traffic[netname] = 0
                        for item in self.real_downstream[netname]:
                            self.real_downstream_traffic[netname] += item[1]

        refresh_thread = Thread(target=refresher)
        refresh_thread.daemon = True
        refresh_thread.start()

    def update_requested_downstream(self, flow):
        ip = _get_flow_ip(flow)
        if ip is None:
            return

        _, resp = get_flow_size(flow)

        netname = _whois(ip, self.org_names)
        with self.lock:
            self.requested_downstream_traffic[netname] += resp
            self.requested_downstream[netname].append((time(), resp))

    def update_requested_upstream(self, flow):
        ip = _get_flow_ip(flow)
        if ip is None:
            return

        req, _ = get_flow_size(flow)

        netname = _whois(ip, self.org_names)
        with self.lock:
            self.requested_upstream_traffic[netname] += req
            self.requested_upstream[netname].append((time(), req))

    def update_real_downstream(self, flow):
        ip = _get_flow_ip(flow)
        if ip is None:
            return

        _, resp = get_flow_size(flow)

        netname = _whois(ip, self.org_names)
        with self.lock:
            self.real_downstream_traffic[netname] += resp
            self.real_downstream[netname].append((time(), resp))

    def update_real_upstream(self, flow):
        ip = _get_flow_ip(flow)
        if ip is None:
            return

        req, _ = get_flow_size(flow)

        netname = _whois(ip, self.org_names)
        with self.lock:
            self.real_upstream_traffic[netname] += req
            self.real_upstream[netname].append((time(), req))

    def reset(self):
        with self.lock:
            for key in self.requested_downstream:
                self.requested_downstream[key].clear()
                self.requested_upstream[key].clear()
                self.real_downstream[key].clear()
                self.real_upstream[key].clear()


class DecoyMaker(object):
    def __init__(self, netstats, org_names):
        self.netstats = netstats
        self.decoy_urls = {}
        self.decoy_sizes = {}
        self.netnames = []

        self.inflight = 0

        for org in org_names:
            self.netnames.append(org)

    def get_decoy_url(self, skip_netname=None):
        flow_netname = skip_netname

        shuffle(self.netnames)

        def key(netname):
            if netname == flow_netname:
                 return 100000
            if netname == 'OTHER':
                return 100000
            if netname not in self.decoy_urls or not len(self.decoy_urls[netname]):
                return 50000
            return self.netstats.requested_upstream_traffic[netname]

        self.netnames.sort(key=key)

        netname = self.netnames[0]
        if netname not in self.decoy_urls or not len(self.decoy_urls[netname]):
            return None

        # return self.decoy_urls[netname][0]

        return choice(self.decoy_urls[netname])

    def record_decoy_sent(self, flow, url):
        flow.estimated_size = self.decoy_sizes[url] 
        self.inflight += flow.estimated_size

    def record_decoy_received(self, flow):
        self.inflight -= flow.estimated_size

    def load_decoys(self, decoys_path):
        import yaml
        import json
        # json loads strings as unicode, causes problems with saving flows
        with open(decoys_path) as f:
            # decoy_urls = yaml.safe_load(f.read())
            decoy_urls = json.loads(f.read())
            for netname in decoy_urls:
                self.decoy_urls[netname] = [str(s) for s in decoy_urls[netname].keys()]
                for url in decoy_urls[netname]:
                    self.decoy_sizes[str(url)] = decoy_urls[netname][url]
                # self.decoy_sizes.update(decoy_urls[netname])


class AdBlocker(object):
    def __init__(self):
        self.single_dom = set()
        self.multi_dom = set()
        self.adset = set()

        self.blacklist = []

    def should_block(self, flow):
        from fnmatch import fnmatch

        domain = urlparse(flow.request.url).netloc

        parts = domain.split('.')
        dom = parts.pop()
        while parts:
            dom = '{}.{}'.format(parts.pop(), dom)
            if dom in self.adset:
                return True

        url = flow.request.url.replace('https://', '').replace('http://', '')
        for pattern in self.blacklist:
            if fnmatch(url, pattern):
                return True

        return False

    def load_blacklist(self, ad_domains_path, blacklist_path):
        with open(ad_domains_path) as f:
            for ad in f:
                ad = ad.strip()
                if not ad: continue
                if ad.count('.') == 1:
                    self.single_dom.add(ad)
                else:
                    self.multi_dom.add(ad)
                self.adset.add(ad)

        with open(blacklist_path) as f:
            for dom in f:
                dom = dom.strip()
                if dom:
                    self.blacklist.append(dom)


def _get_flow_ip(flow):
    if flow.server_conn and flow.server_conn.peer_address:
        return flow.server_conn.peer_address.host

    domain = urlparse(flow.request.url).netloc
    ips, domains = _dig(domain)
    if len(ips):
        return ips[0]
    return None


_whois_cache = {}


def _whois(ip, org_names):
    from ipwhois import IPWhois

    if type(ip) is not str:
        ip = _get_flow_ip(ip)

    if ip not in _whois_cache:
        whois = IPWhois(ip)
        try:
            name = whois.lookup_rdap()['network']['name']
            if not name:
                name = whois.lookup()['nets'][0]['name']
        except:
            print("WHOIS ERROR")
            name = 'OTHER'

        _whois_cache[ip] = _clean_netname(org_names, name, ip)
    return _whois_cache[ip]


def clean_netname(netname):
    """
    Convert a whois netname into an organization name
    """
    # from cdn import cdn_list

    ORGS = [
        ('GOOGLE', ['google']),
        ('AKAMAI', ['akamai', 'umass']),
        ('AMAZON', ['at-', 'amazo']),
        # ('CLOUDFRONT', []),
        ('FASTLY', ['fastly']),
        ('CLOUDFLARE', ['cloudflare']),
        ('EDGECAST', ['edgecast']),
        ('HIGHWINDS', ['highwind']),
        ('INCAPSULA', ['incapsula']),
        ('MAXCDN', ['netdna']),
        ('CDNET', ['cdnet']),
        ('TWITTER', ['twitter']),
        ('INAP', ['inap-']),
        ('LINODE', ['linode']),
        ('DIGITALOCEAN', ['digitalocean']),
        ('YAHOO', ['yahoo']),
        ('FACEBOOK', ['facebook', 'ord1', 'tfbnet']),

        ('OTHER', [])
    ]
    if ' ' in netname:
        netname = netname.split()[0]

    lower = netname.lower()
    for org in ORGS:
        if any([x in lower for x in org[1]]):
            return org[0]

    else:
        org = netname.split()[0]
        # if '-' in org:
        #     org = org[:org.rindex('-')]
        parts = org.split('-')
        if len(parts) < 3:
            org = parts[0]
        elif parts[1].isdigit() :
            org = parts[0]
        else:
            org = parts[0] + '-' + parts[1] #+ '-' + parts[2]

    # if org.startswith('AMAZO') or org.startswith('AT-'):
    #     org = 'AMAZON'
    if org.startswith('WEBAIRINTERNET12'):
        org = 'WEBAIRINTERNET12'

    return org


def _clean_netname(org_names, name, ip):
    org = clean_netname(name)
    if name in org_names:
        return name

    return 'OTHER'


def _parse_dig(raw_dig):
    import re

    if len(raw_dig.strip()) == 0:
        return [], []

    lines = raw_dig.strip().split('\n')

    ip = []
    domains = []
    for line in lines:
        line = line.strip()
        if re.match('^\d+[.]\d+[.]\d+[.]\d+$', line):
            ip.append(line)
        else:
            domains.append(line)

    return ip, domains


def _dig(site, raw=False):
    from subprocess import Popen, PIPE
    process = Popen(["dig", "+short", site], stdout=PIPE)
    (output, err) = process.communicate()
    exit_code = process.wait()

    if raw:
        return output

    return _parse_dig(output)
