import os
import platform

from cachebrowser.util import pkg_data

__all__ = ['settings']


class InsufficientParametersException(Exception):
    pass


class CacheBrowserSettings(dict):
    def __init__(self, *args, **kwargs):
        super(CacheBrowserSettings, self).__init__(*args, **kwargs)

        self.data_dir = platform.get_data_dir()

        self.host = '0.0.0.0'
        self.port = 9876
        self.database = os.path.join(self.data_dir, 'cachebrowser.db')

        self.default_bootstrap_sources = [
            {
                'type': 'local',
                'path': pkg_data.path('local_bootstrap.yaml')
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
