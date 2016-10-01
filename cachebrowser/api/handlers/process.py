

def close(context, request):
    import os
    import signal

    request.reply("OK")
    # sys.exit(0)
    os.kill(os.getpid(), signal.SIGINT)
    os._exit(0)


def ping(context, request):
    request.reply("pong")
