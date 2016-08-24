

def close(request):
    import os
    import signal

    request.reply("OK")
    # sys.exit(0)
    os.kill(os.getpid(), signal.SIGINT)
    os._exit(0)


def ping(request):
    request.reply({'afd': 12})
