#!/usr/bin/env python
import socket

import struct
import sys


def send_to_chrome(message):
    # Write message size.
    sys.stdout.write(struct.pack('I', len(message)))
    # Write the message itself.
    sys.stdout.write(message)
    sys.stdout.flush()


def read_from_chrome():
    text_length_bytes = sys.stdin.read(4)
    if len(text_length_bytes) == 0:
        sys.exit(0)
    # Unpack message length as 4 byte integer.
    text_length = struct.unpack('i', text_length_bytes)[0]
    # Read the text (JSON object) of the message.
    text = sys.stdin.read(text_length).decode('utf-8')
    return text


# sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
# socket_name = '/tmp/cachebrowser.sock'
# sock.connect(socket_name)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 4242))

message = read_from_chrome()
sock.send(message)
sock.send('\n')

# response = ''
# while True:
#     read = sock.recv(1024)
#     if len(read) == 0:
#         break
#     response += read

response = sock.recv(1024)
send_to_chrome(response)

# send_to_chrome("{}")
