import json
import logging
from core import cli
from core import stream
from core import api


def handle_connection(connection, address):
    streamer = stream.LineStreamer()

    logging.info("New connection established")

    while True:
        data = connection.recv(1024)
        if not data:
            break

        streamer.append(data)
        while streamer.has_message():
            message = streamer.next_message()
            try:
                message = json.loads(message)
                api.handle_message(connection, message)
            except ValueError:
                cli.handle_message(connection, message)
        # connection.close()