__all__ = ['settings']


class InsufficientParametersException(Exception):
    pass


class CacheBrowserSettings(dict):
    def __init__(self, *args, **kwargs):
        super(CacheBrowserSettings, self).__init__(*args, **kwargs)

        # Set defaults
        self['socket'] = '/tmp/cachebrowser.sock'
        self['host'] = '0.0.0.0'
        self['port'] = 9876
        self['database'] = '/tmp/cachebrowser.db'

    def get_or_error(self, key):
        if self.get(key, None):
            return self[key]
        raise InsufficientParametersException("Missing parameter %s" % key)

    def update_from_args(self, args):
        for key in args:
            val = args[key]
            if val:
                self[key] = val


settings = CacheBrowserSettings()