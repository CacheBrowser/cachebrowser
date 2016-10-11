from __future__ import print_function, absolute_import

import logging
import logging.config
import sys
import inspect
import os

import click
import mitmproxy
import mitmproxy.controller
from mitmproxy.proxy.server import ProxyServer

from cachebrowser.bootstrap import Bootstrapper
from cachebrowser.models import initialize_database
from cachebrowser.proxy import ProxyController, ProxyConfig
from cachebrowser.pipes.resolver import ResolverPipe
from cachebrowser.pipes.publisher import PublisherPipe
from cachebrowser.pipes.sni import SNIPipe
from cachebrowser.pipes.website_filter import WebsiteFilterPipe
from cachebrowser.settings import DevelopmentSettings, ProductionSettings, SettingsValidationError
from cachebrowser.ipc import IPCManager
from cachebrowser.api.routes import routes as api_routes
from cachebrowser import cli

logger = logging.getLogger(__name__)


class Context(object):
    def __init__(self):
        self.click = None
        self.settings = None
        self.bootstrapper = None


@click.group(invoke_without_command=True)
@click.option('-c', '--config', type=click.File('r'), help="Path to configuration file.")
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.option('-p', '--port', type=int, help='The HTTP proxy port to run on.')
@click.option('-d', '--database', type=str, help="Path to store database file.")
@click.option('--sni', type=click.Choice(['empty', 'front', 'original']), help="The default SNI policy to use.")
@click.option('--reset-db', is_flag=True, default=False, help="Reset the database.")
@click.option('--dev', is_flag=True, default=False, help="Run in development mode.")
@click.pass_context
def cachebrowser(click_context, config, verbose, reset_db, dev, **kwargs):
    settings = DevelopmentSettings() if dev else ProductionSettings()

    if config is None and os.path.isfile(settings.data_path('config.yaml')):
        config = open(settings.data_path('config.yaml'))

    try:
        settings.update_with_settings_file(config)
        settings.update_with_args(kwargs)
        settings.validate()
    except SettingsValidationError as e:
        print("Error parsing settings")
        print(e.message)
        sys.exit(1)

    initialize_logging(verbose)

    if not dev:
        check_data_files(settings)

    logger.debug("Initializing database")
    initialize_database(settings.database, reset_db)

    logger.debug("Initializing bootstrapper")
    bootstrapper = Bootstrapper(settings)

    context = Context()
    context.bootstrapper = bootstrapper
    context.settings = settings
    context.click = click_context

    click_context.obj = context

    if click_context.invoked_subcommand is None:
        logger.debug("No command specified, starting CacheBrowser server")
        click_context.invoke(start_cachebrowser_server)


@cachebrowser.command('start')
@click.pass_obj
def start_cachebrowser_server(context):
    logger.debug("Initializing IPC")
    ipc = IPCManager(context)
    ipc.register_rpc_handlers(api_routes)

    config = ProxyConfig(context)
    server = ProxyServer(config)
    m = ProxyController(server, ipc)

    # logger.debug("Adding WebsiteFilter Pipe")
    # m.add_pipe(WebsiteFilterPipe(context))
    logger.debug("Adding 'Resolver' pipe")
    m.add_pipe(ResolverPipe(context))
    logger.debug("Adding 'SNI' pipe")
    m.add_pipe(SNIPipe(context))
    logger.debug("Adding 'Publisher' pipe")
    m.add_pipe(PublisherPipe(context))

    try:
        logger.info("Listening for proxy connections on port {}".format(context.settings.port))
        return m.run()
    except KeyboardInterrupt:
        m.shutdown()


def initialize_logging(verbose=False):
    level = 'DEBUG' if verbose else 'INFO'
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,  # this fixes the problem

        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': level,
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': level,
                'propagate': True
            }
        }
    })


def check_data_files(settings):
    import os
    import pkgutil

    if not os.path.isdir(settings.data_dir()):
        try:
            os.mkdir(settings.data_dir())
        except OSError:
            logger.error("Creating data directory failed", exc_info=True)
            sys.exit(1)

    data_files = [
        'local_bootstrap.yaml'
    ]

    for data_file in data_files:
        data_path = settings.data_path(data_file)

        if not os.path.isfile(data_path):
            logger.info("Creating data file {}".format(data_path))
            with open(data_path, 'w') as f:
                f.write(pkgutil.get_data('cachebrowser', os.path.join('data', data_file)))


for name in cli.main_commands:
    cachebrowser.add_command(getattr(cli, name))
