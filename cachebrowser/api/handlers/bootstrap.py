from cachebrowser.models import Host, CDN


def serialize_host(host):
    return {
        'hostname': host.hostname,
        'cdn': {'id': host.cdn.id, 'name': host.cdn.name} if host.cdn else None,
        'ssl': host.ssl,
    }


def serialize_cdn(cdn):
    return {
        'id': cdn.id,
        'name': cdn.name,
        'edge_server': cdn.edge_server,
    }


def get_hosts(context, request):
    page = request.params.get('page', 0)
    num_per_page = request.params.get('num_per_page', 5)

    if num_per_page <= 0:
        result = Host.select()
    else:
        result = Host.select().paginate(page, num_per_page)
    hosts = [serialize_host(host) for host in result]

    request.reply(hosts)


def delete_host(context, request):
    hostname = request.params.get('host', '')
    Host.delete().where(Host.hostname == hostname).execute()
    request.reply()


def add_host(context, request):
    host = Host()
    host.hostname = request.params.get('hostname', '')
    host.cdn = request.params.get('cdn', '')
    host.ssl = request.params.get('ssl', True)

    host.save(force_insert=True)
    request.reply()


def get_cdns(context, request):
    page = request.params.get('page', 0)
    num_per_page = request.params.get('num_per_page', 5)

    if num_per_page <= 0:
        result = CDN.select()
    else:
        result = CDN.select().paginate(page, num_per_page)
    cdns = [serialize_cdn(cdn) for cdn in result]

    request.reply(cdns)


def add_cdn(context, request):
    cdn = CDN()
    cdn.id = request.params.get('id', '')
    cdn.name = request.params.get('name', '')
    cdn.edge_server = request.params.get('edge_server', True)

    cdn.save(force_insert=True)
    request.reply()
