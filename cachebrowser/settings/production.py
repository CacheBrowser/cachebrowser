import appdirs

from cachebrowser.settings.base import APP_NAME, CacheBrowserSettings


class ProductionSettings(CacheBrowserSettings):
    def set_defaults(self):
        self.host = "127.0.0.1"
        self.port = 8080
        self.database = self.data_path('cachebrowser.db')
        self.bootstrap_sources = [
            {
                'type': 'local',
                'path': self.data_path('local_bootstrap.yaml')
            }
        ]

    def data_dir(self):
        return appdirs.user_data_dir(APP_NAME)
