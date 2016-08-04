import os
import sys

APP_NAME = "CacheBrowser"


class UnsupportedPlatform(Exception):
    pass


def get_data_dir(create=True):
    platform = sys.platform

    if platform == 'darwin':
        data_dir = os.path.expanduser('~/Library/Application Support/{}'.format(APP_NAME))
    elif platform == 'windows':
        data_dir = os.path.join(os.environ.get('ALLUSERSPROFILE', ''), APP_NAME)
    elif platform == 'linux':
        data_dir = os.path.expanduser('~/.{}'.format(APP_NAME.lower()))
    else:
        raise UnsupportedPlatform()

    if not os.path.isdir(data_dir):
        os.mkdir(data_dir)

    return data_dir
