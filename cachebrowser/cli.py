from functools import update_wrapper, partial
import json
import logging
from cachebrowser.models import Host

import click

from cachebrowser.api.core import APIManager, APIRequest
from cachebrowser.bootstrap import BootstrapError

main_commands = ['hostcli', 'cdncli', 'bootstrap']

api = APIManager()
logger = logging.getLogger(__name__)


def forward_to_api(route, params=None):
    def wrapper(func):
        @click.pass_obj
        def inner(context, **kwargs):
            request_params = params.copy() if params else {}
            request_params.update(kwargs)
            request = APIRequest(route, request_params)
            request.reply = partial(func, context)
            api.handle_api_request(context, request)

        return update_wrapper(inner, func)

    return wrapper


@click.group('host')
def hostcli():
    pass


@hostcli.command('add')
@forward_to_api('/hosts/add')
@click.argument('hostname')
@click.argument('cdn')
@click.option('--ssl/--no-ssl', 'ssl', default=True)
def addhost(context):
    click.echo("New host added")


@hostcli.command('list')
@forward_to_api('/hosts', {'page': 0, 'num_per_page': 0})
def listhost(context, hosts):
    click.echo('\n'.join([host['hostname'] for host in hosts]))


@click.group('cdn')
def cdncli():
    pass


@cdncli.command('add')
@forward_to_api('/cdns/add')
@click.argument('id')
@click.option('--name')
@click.option('--edge-server')
def addcdn(context):
    click.echo("New CDN added")


@cdncli.command('list')
@forward_to_api('/cdns', {'page': 0, 'num_per_page': 0})
def listhost(context, cdns):
    click.echo('\n'.join([cdn['id'] for cdn in cdns]))


@click.command('bootstrap')
@click.option('--save/--no-save', is_flag=True, default=False,
              help="Save bootstrap information to database (default --no-save)")
@click.argument('hostname')
@click.pass_obj
def bootstrap(context, save, hostname):
    try:
        host_data = context.bootstrapper.lookup_host(hostname)
    except BootstrapError:
        logger.warning("No bootstrap information found for host '{}'".format(hostname))
        return

    logger.info(json.dumps(host_data, indent=4))

    if save:
        host = Host(**host_data)
        host.save()
