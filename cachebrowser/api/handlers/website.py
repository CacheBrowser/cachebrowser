from cachebrowser.models import Website


def enable_website(context, request):
    hostname = request.params.get('website', None)

    if hostname is None:
        return request.reply({'result': 'error', 'message': 'no website given'})

    website, _ = Website.get_or_create(hostname=hostname)

    if not website.enabled:
        website.enabled = True
        website.save()
    request.reply({'result': 'success'})


def disable_website(context, request):
    hostname = request.params.get('website', None)

    if hostname is None:
        return request.reply({'result': 'error', 'message': 'no website given'})

    website, _ = Website.get_or_create(hostname=hostname)

    if website.enabled:
        website.enabled = False
        website.save()
    request.reply({'result': 'success'})


def is_website_enabled(context, request):
    hostname = request.params.get('website', None)

    if hostname is None:
        return request.reply({'result': 'error', 'message': 'no website given'})

    website, _ = Website.get_or_create(hostname=hostname)
    request.reply({'result': 'success', 'enabled': website.enabled})


