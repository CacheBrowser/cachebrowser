from functools import partial
import os
import logging
import re
import sys
import yaml
from cachebrowser.pipes.sni import SNI_EMPTY, SNI_ORIGINAL, SNI_FRONT

APP_NAME = "CacheBrowser"

logger = logging.getLogger(__name__)


class InsufficientParametersException(Exception):
    pass


class SettingsValidationError(Exception):
    pass


class CacheBrowserSettings(object):
    def __init__(self):
        self.host = None
        self.port = None
        self.ipc_port = None
        self.database = None
        self.bootstrap_sources = []

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
        data_dir = self.data_dir()
        return data_dir if path is None else os.path.join(data_dir, path)

    def read_bootstrap_sources(self, args):
        local_sources = args.get('local_bootstrap') or []
        for source in local_sources:
            self.bootstrap_sources.append({
                'type': 'local',
                'path': source
            })

    def validate(self):
        if not re.match('\d+[.]\d+[.]\d+[.]\d+', self.host):
            raise SettingsValidationError(
                "invalid host ip address '{}'".format(self.host))

        if type(self.port) != int or not 0 < self.port < 65536:
            raise SettingsValidationError(
                "invalid port number '{}'".format(self.port))

        if type(self.ipc_port) != int or not 0 < self.port < 65536:
            raise SettingsValidationError(
                "invalid ipc port number '{}'".format(self.ipc_port))

        if self.default_sni_policy not in [SNI_EMPTY, SNI_FRONT, SNI_ORIGINAL]:
            raise SettingsValidationError(
                "invalid default sni policy '{}".format(self.default_sni_policy))

    def update_with_settings_file(self, config_file):
        if not config_file:
            return
        try:
            config = yaml.load(config_file)
        except yaml.scanner.ScannerError as e:
            raise SettingsValidationError(
                "Invalid config file, not in valid YAML format\n{}".format(e))

        update = partial(self._update_arg, config)
        update_path = partial(self._update_path_arg, config)

        update('host')
        update('port')
        update_path('database')
        update('default_sni_policy', 'sni_policy')

        self._update_bootstrap_sources(config.pop('bootstrap_sources', None))

        if config:
            raise SettingsValidationError(
                "Invalid parameter in config file: '{}'".format(config.keys()[0])
            )

    def update_with_args(self, config):
        config = config.copy()
        update = partial(self._update_arg, config)

        update('host')
        update('port')
        update('database')
        update('default_sni_policy', 'sni')

    def _update_arg(self, conf, param, confparam=None):
        value = conf.pop((confparam or param).lower(), None)
        if value is not None:
            setattr(self, param, value)

    def _update_path_arg(self, conf, param, confparam=None):
        value = conf.pop((confparam or param).lower(), None)
        if value is not None:
            if not os.path.isabs(value):
                value = self.data_path(value)
            setattr(self, param, value)

    def _update_bootstrap_sources(self, bootstrap_sources):
        if bootstrap_sources is None:
            return

        for source in bootstrap_sources:
            if 'type' not in source:
                raise SettingsValidationError(
                    "Missing 'type' field in bootstrap source")
            if source['type'] == 'local':
                path = source.get('path', None)
                if path is None:
                    raise SettingsValidationError(
                        "Missing 'path' for local bootstrap source")
                # change relative paths to absolute ones
                # (all relative paths in config files are relative to data dir
                if not os.path.isabs(path):
                    source['path'] = self.data_path(path)

            elif source['type'] == 'remote':
                if source.get('url') is None:
                    raise SettingsValidationError(
                        "Missing 'url' for remote bootstrap source")

            self.bootstrap_sources.append(source)

settings = CacheBrowserSettings()

