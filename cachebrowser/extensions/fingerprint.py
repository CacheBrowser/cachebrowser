import json
import urlparse

from cachebrowser import common, http, dns
import sys
import time
from datetime import datetime

#
# handlers = set()
#
# def request_wrapper(request):
#     def inner(url, **kwargs):
#         parsed_url = urlparse.urlparse(url)
#         target, cachebrowsed = dns.resolve_host(parsed_url.hostname, use_cachebrowser_db=False)
#         kwargs['target'] = target
#         kwargs['cachebrowse'] = False
#
#         for handler in handlers:
#             handler.log(url, target)
#
#         return request(url, **kwargs)
#     return inner
#
#
# # Wrap request method
# http.request = request_wrapper(http.request)
from cachebrowser.proxybeta import proxy_logger

rack = common.context.get('server_rack')
cli_server = rack.get_server('cli')
cli_handler_class = cli_server.handler

api_server = rack.get_server('api')
api_handler_class = api_server.handler


class Recorder():
    def __init__(self):
        self.logging = False
        self.data_sets = None
        self.targets = []

    def log(self, host, target, scheme, url, cachebrowsed, **kwargs):
        if not self.logging:
            return
        self.targets.append({
            'host': host,
            'url': url,
            'ip': target,
            'scheme': scheme,
            'cachebrowsed': cachebrowsed
        })

    def start_recording(self):
        self.logging = True
        self.targets = []
        self.data_sets = None

    def stop_recording(self):
        self.logging = False
        data = {'timestamp': int(time.time()), 'date': str(datetime.now()), 'connections': self.targets}
        self.data_sets = data

    def results(self):
        return self.data_sets


recorder = Recorder()
proxy_logger.register_handler(recorder.log)
# handlers.add(recorder.log)


class CLIHandler(cli_handler_class):
    def __init__(self, *args, **kwargs):
        super(CLIHandler, self).__init__(*args, **kwargs)
        self.register_command('fp start', self.fp_start)
        self.register_command('fp stop', self.fp_stop)
        self.register_command('fp save', self.fp_save)
        # self.register_command('fp run', self.fp_auto_run)
        self.logging = False
        self.data_sets = []
        self.targets = []

    def on_connect(self, *args, **kwargs):
        super(CLIHandler, self).on_connect(*args, **kwargs)
        handlers.add(self)

    def on_close(self, *args, **kwargs):
        super(CLIHandler, self).on_close(*args, **kwargs)
        handlers.remove(self)

    def log(self, url, target):
        if not self.logging:
            return
        self.targets.append({
            'url': url,
            'ip': target
        })

    def fp_start(self):
        self.logging = True
        self.targets = []
        self.data_sets = []

    def fp_stop(self, host):
        self.logging = False

        data = {
            'host': host,
            'timestamp': time.time()
        }

        for target in self.targets:
            from ipwhois import IPWhois
            try:
                whois = IPWhois(target['ip'])
                name = whois.lookup_rdap()['network']['name']
                target['org'] = name
            except:
                print("EXCEPTION")
                sys.exit(1)

        data['connections'] = self.targets
        self.data_sets.append(data)
        self.send_line("Saved as %s" % host)

    def fp_save(self, push_server='http://www.cachebrowser.info/fp/', **kwargs):
        import requests

        url = "%s/records/" % push_server
        for dataset in self.data_sets:
            data = dataset
            for key in kwargs:
                data[key] = kwargs[key]

            if data.has_key('tags'):
                data['tags'] = data['tags'].split(',')

            data_json = json.dumps(data)
            headers = {'Content-type': 'application/json'}
            response = requests.post(url, data=data_json, headers=headers)
            if response.status_code == 200:
                self.send_line("Posted %s to server" % data['host'])
            else:
                self.send_line("Saving %s failed: %d %s" % (data['host'], response.status_code, response.reason))


class APIHandler(api_handler_class):
    def __init__(self, *args, **kwargs):
        super(APIHandler, self).__init__(*args, **kwargs)
        self.register_api('POST', '/record/start', self.fp_start)
        self.register_api('POST', '/record/stop', self.fp_stop)
        self.register_api('GET', '/record/results', self.fp_results)

    def fp_start(self, message):
        try:
            recorder.start_recording()
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'fail', 'error': e.message}

    def fp_stop(self, message):
        try:
            recorder.stop_recording()
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'fail', 'error': e.message}

    def fp_results(self, message):
        try:
            results = recorder.results()
            return {'status': 'ok', 'results': results}
        except Exception as e:
            return {'status': 'fail', 'error': e.message}

cli_server.handler = CLIHandler
api_server.handler = APIHandler


