import os
import platform

__all__ = ['settings']


class InsufficientParametersException(Exception):
    pass


class CacheBrowserSettings(dict):
    def __init__(self, *args, **kwargs):
        super(CacheBrowserSettings, self).__init__(*args, **kwargs)

        if platform.system() == 'Windows':
            self.data_dir = os.path.join(os.environ['ALLUSERSPROFILE'], 'CacheBrowser')
        else:
            self.data_dir = '/tmp/'

        # Set defaults
        self['host'] = '0.0.0.0'
        self['port'] = 9876
        self['database'] = os.path.join(self.data_dir, 'cachebrowser.db')

        # Use attributes instead of dictionary values
        self.host = '0.0.0.0'
        self.port = 9876
        self.database = os.path.join(self.data_dir, 'cachebrowser.db')

        self.default_bootstrap_sources = [
            {
                'type': 'local',
                'path': 'data/local_bootstrap.yaml'
            },
            {
                'type': 'remote',
                'url': 'https://www.cachebrowser.info/bootstrap'
            }
        ]

        self.bootstrap_sources = []

    def get_or_error(self, key):
        if self.get(key, None):
            return self[key]
        raise InsufficientParametersException("Missing parameter %s" % key)

    def update_from_args(self, args):
        self.host = self._read_arg(args, 'host', self.host)
        self.port = self._read_arg(args, 'port', self.port)
        self.database = self._read_arg(args, 'database', self.database)

        self.read_bootstrap_sources(args)

    def read_bootstrap_sources(self, args):
        local_sources = args.get('local_bootstrap') or []
        for source in local_sources:
            self.bootstrap_sources.append({
                'type': 'local',
                'path': source
            })

    @staticmethod
    def _read_arg(args, key, default):
        try:
            return args[key]
        except KeyError:
            return default


settings = CacheBrowserSettings()