import unittest
from cachebrowser.bootstrap import LocalBootstrapSource, BootstrapSourceError, BaseBootstrapSource, Bootstrapper, \
    BootstrapValidationError, HostNotAvailableError, CDNNotAvailableError
from cachebrowser.models import initialize_database, Host, CDN


class LocalBootstrapSourceTest(unittest.TestCase):

    def test_valid_file(self):
        local_source = LocalBootstrapSource('data/bootstrap/valid.yaml')

        host = local_source.lookup_host('www.test.com')
        self.assertEqual('testcdn', host['cdn'])
        self.assertEqual(True, host['uses_ssl'])

        cdn = local_source.lookup_cdn('testcdn')
        self.assertEqual('Test CDN', cdn['name'])
        self.assertEqual('1.2.3.4', cdn['edge_server'])

        self.assertIsNone(local_source.lookup_host("doesntexist"))
        self.assertIsNone(local_source.lookup_cdn("doesntexist"))

    def test_no_type(self):
        with self.assertRaises(BootstrapSourceError):
            LocalBootstrapSource('data/bootstrap/no_type.yaml')

    def test_host_no_name(self):
        with self.assertRaises(BootstrapSourceError):
            LocalBootstrapSource('data/bootstrap/host_no_name.yaml')

    def test_host_no_cdn(self):
        with self.assertRaises(BootstrapSourceError):
            LocalBootstrapSource('data/bootstrap/host_no_cdn.yaml')

    def test_cdn_no_id(self):
        with self.assertRaises(BootstrapSourceError):
            LocalBootstrapSource('data/bootstrap/cdn_no_id.yaml')


class BootstrapperTest(unittest.TestCase):

    def setUp(self):
        initialize_database(":memory:", reset=True)

        self.source = BaseBootstrapSource()

        def lookup_host(hostname):
            return {
                'the.host': {
                    'hostname': 'the.host',
                    'uses_ssl': True,
                    'cdn': 'thecdn'
                },
                'missingcdn.host': {
                    'hostname': 'missingcdn.host',
                    'cdn': 'missingcdn'
                },
                'invalid.host': {
                    'hostname': 'invalid.host',
                    'uses_ssl': True,
                },
                'mismatch.host': {
                    'hostname': 'the.host',
                    'uses_ssl': True,
                    'cdn': 'thecdn'
                },
                'badcdn.host': {
                    'hostname': 'badcdn.host',
                    'cdn': 'invalidcdn'
                }
            }.get(hostname, None)

        def lookup_cdn(cdn_id):
            return {
                'thecdn': {
                    'id': 'thecdn',
                    'name': 'The CDN',
                    'edge_server': '1.2.3.4'
                },
                'invalidcdn': {
                    'name': 'The CDN',
                    'edge_server': '1.2.3.4'
                },
            }.get(cdn_id, None)

        self.source.lookup_host = lookup_host
        self.source.lookup_cdn = lookup_cdn

        self.bootstrapper = Bootstrapper()
        self.bootstrapper.add_source(self.source)

    def test_bootstrap(self):
        self.bootstrapper.bootstrap('the.host')

        self.assertTrue(Host.select().where(Host.hostname == 'the.host').exists())
        self.assertTrue(CDN.select().where(CDN.id == 'thecdn').exists())

    def test_unavailable_host__host_not_in_db(self):
        with self.assertRaises(HostNotAvailableError):
            self.bootstrapper.bootstrap('doesnt.exist')

    def test_unavailable_host__host_in_db__unavailable_cdn__cdn_in_db_with_no_edge(self):
        cdn = CDN.create(id="missingcdn")
        Host.create(hostname="host.db", cdn=cdn)

        with self.assertRaises(CDNNotAvailableError):
            self.bootstrapper.bootstrap('missingcdn.host')

    def test_unavailable_host__host_in_db__available_cdn__cdn_in_db_with_no_edge(self):
        cdn = CDN.create(id="thecdn")
        Host.create(hostname="host.db", cdn=cdn)
        self.bootstrapper.bootstrap('host.db')

    def test_invalid_hostname(self):
        with self.assertRaises(BootstrapValidationError):
            self.bootstrapper.bootstrap('http://someinvalid.host')

    def test_invalid_host_data(self):
        with self.assertRaises(BootstrapValidationError):
            self.bootstrapper.bootstrap('invalid.host')

    def test_hostname_mismatch(self):
        with self.assertRaises(BootstrapValidationError):
            self.bootstrapper.bootstrap('mismatch.host')

    def test_invalid_cdn_data(self):
        with self.assertRaises(BootstrapValidationError):
            self.bootstrapper.bootstrap('badcdn.host')