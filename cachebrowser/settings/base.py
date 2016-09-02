import os

APP_NAME = "CacheBrowser"


class InsufficientParametersException(Exception):
    pass


class CacheBrowserSettings(object):
    def __init__(self):
        self.host = None
        self.port = None
        self.ipc_port = None
        self.database = None
        self.bootstrap_sources = None

        self.default_sni_policy = "original"

        self.set_defaults()

    def set_defaults(self):
        """
        Implemented by subclasses
        """

    def data_dir(self):
        """
        Implemented by subclasses
        :return:
        """

    def data_path(self, path=None):
        data_directory = self.data_dir()
        return data_directory if path is None else os.path.join(data_directory, path)

    def read_bootstrap_sources(self, args):
        local_sources = args.get('local_bootstrap') or []
        for source in local_sources:
            self.bootstrap_sources.append({
                'type': 'local',
                'path': source
            })

    def update_with_settings_file(self, settings_module):
        # TODO Implement
        pass

    def update_with_args(self):
        # TODO Implement
        pass

settings = CacheBrowserSettings()
