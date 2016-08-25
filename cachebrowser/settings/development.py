from cachebrowser.settings.base import CacheBrowserSettings


class DevelopmentSettings(CacheBrowserSettings):
    def set_defaults(self):
        self.host = "127.0.0.1"
        self.port = 9000
        self.database = 'db.sqlite'
        self.bootstrap_sources = [
            {
                'type': 'local',
                'path': self.data_path('local_bootstrap.yaml')
            },
            {
                'type': 'remote',
                'url': 'http://localhost:3000/api'
            }
        ]

    def data_dir(self):
        return 'data'
