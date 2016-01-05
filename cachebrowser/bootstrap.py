import json
import os
import random
import urllib
import yaml
from yaml.scanner import ScannerError
from cachebrowser.common import logger

from cachebrowser.settings import settings
from cachebrowser.models import Host, CDN, DoesNotExist
from cachebrowser.http import request


class BootstrapSourceError(Exception):
    pass


class BaseBootstrapSource(object):
    def lookup_host(self, hostname):
        pass

    def lookup_cdn(self, cdn_id):
        pass


class LocalBootstrapSource(BaseBootstrapSource):
    ERROR_PREFIX = "while parsing local bootstrap source file.\n"

    def __init__(self, filename):
        super(LocalBootstrapSource, self).__init__()
        self.hosts = {}
        self.cdns = {}

        self.filename = filename
        self._load_source(filename)

    def lookup_host(self, hostname):
        return self.hosts.get(hostname, None)

    def lookup_cdn(self, cdn_id):
        cdn = self.cdns.get(cdn_id, None)
        if cdn is not None and len(cdn['edge_servers']) > 0:
            return {
                'id': cdn['id'],
                'name': cdn['name'],
                'edge_server': random.choice(cdn['edge_servers'])
            }

        return None

    def _load_source(self, filename):
        try:
            with open(filename, 'r') as stream:
                raw_data = yaml.load(stream)
            self._parse_raw_data(raw_data)
        except ScannerError as e:
            raise BootstrapSourceError(self.ERROR_PREFIX + "Error %s" % e.message)

    def _parse_raw_data(self, raw_data):
        if type(raw_data) == list:
            self._parse_list_data(raw_data)

    def _parse_list_data(self, raw_data):
        for entry in raw_data:
            if 'type' not in entry:
                raise BootstrapSourceError(self.ERROR_PREFIX + "No type defined for entry")

            entry_type = entry['type']
            if entry_type == 'host':
                self._parse_host_entry(entry)
            elif entry_type == 'cdn':
                self._parse_cdn_entry(entry)
            else:
                raise BootstrapSourceError(self.ERROR_PREFIX + "Invalid type: '%s'" % entry_type)

    def _parse_host_entry(self, host_data):
        if 'name' not in host_data:
            raise BootstrapSourceError(self.ERROR_PREFIX + "Missing key 'name' on host item")
        if 'cdn' not in host_data:
            raise BootstrapSourceError(self.ERROR_PREFIX + "Missing key 'cdn' on host item")

        host = {
            'hostname': host_data['name'],
            'cdn': host_data['cdn'],
        }

        if 'ssl' in host_data:
            host['ssl'] = host_data['ssl']

        self.hosts[host['hostname']] = host

    def _parse_cdn_entry(self, cdn_data):
        if 'id' not in cdn_data:
            raise BootstrapSourceError(self.ERROR_PREFIX + "Missing key 'id' on cdn item")

        cdn = {
            'id': cdn_data['id'],
            'name': cdn_data.get('name', ''),
            'edge_servers': cdn_data.get('edge_servers', [])
        }

        self.cdns[cdn['id']] = cdn

    def __str__(self):
        return self.filename


class RemoteBootstrapSource(BaseBootstrapSource):
    def __init__(self, server_url):
        super(RemoteBootstrapSource, self).__init__()

        if '://' not in server_url:
            raise BootstrapSourceError('Invalid remote bootstrap server URL')

        self.server_url = server_url

    def lookup_host(self, hostname):
        return self._request('host/%s' % hostname)

    def lookup_cdn(self, cdn_id):
        return self._request('cdn/%s' % cdn_id)

    def _request(self, path):
        response = request(os.path.join(self.server_url, path))
        if response.status == 404:
            return None
        elif response.status != 200:
            raise BootstrapSourceError('Remote bootstrapper request failed: %d' % response.status)

        try:
            return json.loads(response.read())
        except ValueError:
            raise BootstrapSourceError('Invalid JSON response from remote bootstrap server')

    def __str__(self):
        return self.server_url


class BootstrapError(Exception):
    pass


class HostNotAvailableError(BootstrapError):
    def __init__(self, host):
        super(HostNotAvailableError, self).__init__("Host '%s' not available" % host)


class CDNNotAvailableError(BootstrapError):
    def __init__(self, cdn_id):
        super(CDNNotAvailableError, self).__init__("CDN '%s' not available" % cdn_id)


class BootstrapValidationError(BootstrapError):
    pass


class Bootstrapper(object):
    CDN = CDN
    Host = Host

    def __init__(self):
        self.sources = []

    def add_source(self, source):
        self.sources.append(source)

    def bootstrap(self, hostname):
        hostname = self._validate_host_name(hostname)
        host_source = None

        # Lookup Host from sources
        try:
            host_data, host_source = self._lookup_host(hostname)
            host, host_created = self._get_or_create_host(hostname, create=True)
            host.uses_ssl = host_data['ssl']

            cdn, cdn_created = self._get_or_create_cdn(host_data['cdn'], create=True)
            host.cdn = cdn
        except HostNotAvailableError:
            host, host_created = self._get_or_create_host(hostname, create=False)
            if not host:
                raise

            cdn, cdn_created = host.cdn, False

        # Bootstrap CDN from sources
        if cdn_created or cdn.edge_server is None:
            try:
                cdn_data, cdn_source = self._lookup_cdn(cdn.id)
                cdn.name = cdn_data['name']
                cdn.edge_server = cdn_data['edge_server']
                cdn.save()

                logger.info("CDN '%s' bootstrapped from '%s'" % (cdn, str(cdn_source)))
            except CDNNotAvailableError:
                host.is_active = False
                host.save()
                raise

        host.is_active = True
        host.save()

        if host_source is not None:
            logger.info("Host '%s' bootstrapped from '%s'" % (host, str(host_source)))
        return host

    def _lookup_host(self, hostname):
        for source in self.sources:
            host_data = source.lookup_host(hostname)
            if host_data:
                return self._validate_host_data(hostname, host_data), source
        raise HostNotAvailableError(hostname)

    def _lookup_cdn(self, cdn_id):
        for source in self.sources:
            cdn_data = source.lookup_cdn(cdn_id)
            if cdn_data:
                return self._validate_cdn_data(cdn_id, cdn_data), source
        raise CDNNotAvailableError(cdn_id)

    @classmethod
    def _get_or_create_host(cls, hostname, create=True):
        try:
            return Host.get(Host.hostname == hostname), False
        except DoesNotExist:
            if create:
                return Host.create(hostname=hostname), True
            return None, None

    @classmethod
    def _get_or_create_cdn(cls, cdn_id, create=True):
        try:
            return CDN.get(CDN.id == cdn_id), False
        except DoesNotExist:
            if create:
                return CDN.create(id=cdn_id), True
            return None, None

    @classmethod
    def _validate_host_name(cls, hostname):
        if any(s in hostname for s in ['http', '/']):
            raise BootstrapValidationError("invalid hostname to be bootstrapped: '%s'" % hostname)
        return hostname

    @classmethod
    def _validate_host_data(cls, hostname, host_data):
        for key in ['hostname', 'cdn']:
            if key not in host_data:
                raise BootstrapValidationError("invalid host data received, missing '%s' key" % key)

        if hostname != host_data['hostname']:
                raise BootstrapValidationError("host data mismatch. Expecting data for %s but got data for %s"
                                               % (hostname, host_data['hostname']))

        host_data.setdefault('ssl', False)

        return host_data

    @classmethod
    def _validate_cdn_data(cls, cdn_id, cdn_data):
        for key in ['id', 'edge_server']:
            if key not in cdn_data:
                raise BootstrapValidationError("invalid cdn data received, missing '%s' key" % key)

        if cdn_id != cdn_data['id']:
            raise BootstrapValidationError("host data mismatch. Expecting data for %s but got data for %s"
                                           % (cdn_id, cdn_data['id']))
        return cdn_data


bootstrapper = Bootstrapper()


def initialize_bootstrapper(bootstrapper=bootstrapper):
    sources = settings.default_bootstrap_sources
    sources += settings.bootstrap_sources

    for source_config in sources:
        if source_config['type'] == 'local':
            source = LocalBootstrapSource(source_config['path'])
        elif source_config['type'] == 'remote':
            source = RemoteBootstrapSource(source_config['url'])
        bootstrapper.add_source(source)
