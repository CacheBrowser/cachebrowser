__all__ = ['options']


class InsufficientParametersException(Exception):
    pass


class CacheBrowserOptions(dict):
    def __init__(self, *args, **kwargs):
        super(CacheBrowserOptions, self).__init__(*args, **kwargs)

        # Set defaults
        self['socket'] = '/tmp/cachebrowser.sock'

    def get_or_error(self, key):
        if self.get(key, None):
            return self[key]
        raise InsufficientParametersException("Missing parameter %s" % key)

    def update_from_args(self, args):
        for key in args:
            val = args[key]
            if val:
                self[key] = val


options = CacheBrowserOptions()