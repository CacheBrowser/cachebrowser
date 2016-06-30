from cachebrowser.models import Host, CDN


def serialize_host(host):
    return {
        'hostname': host.hostname,
        'cdn': {'id': host.cdn.id, 'name': host.cdn.name} if host.cdn else None,
        'ssl': host.ssl
    }


def get_hosts(request):
    page = request.params.get('page', 0)
    num_per_page = request.params.get('num_per_page', 5)

    result = Host.select().paginate(page, num_per_page)  # .order_by(Host.hostname)
    hosts = [serialize_host(host) for host in result]

    request.reply(hosts)


def delete_host(request):
    hostname = request.params.get('host', '')
    Host.delete().where(Host.hostname == hostname).execute()
    request.reply()


def add_host(request):
    host = Host()
    host.hostname = request.params.get('hostname', '')
    host.cdn = request.params.get('cdn', '')
    host.ssl = request.params.get('ssl', True)

    host.save(force_insert=True)
    request.reply()


def add_cdn(request):
    cdn = CDN()
    cdn.id = request.params.get('id', '')
    cdn.name = request.params.get('name', '')
    cdn.edge_server = request.params.get('edge_server', True)

    cdn.save(force_insert=True)
    request.reply()
