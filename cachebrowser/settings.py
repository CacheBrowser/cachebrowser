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
                'url': 'http://localhost:3000/api'
            }
        ]

        # self.bootstrap_sources = []
        self.bootstrap_sources = self.default_bootstrap_sources

    def read_bootstrap_sources(self, args):
        local_sources = args.get('local_bootstrap') or []
        for source in local_sources:
            self.bootstrap_sources.append({
                'type': 'local',
                'path': source
            })



settings = CacheBrowserSettings()