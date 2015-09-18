
class MessageStreamer(object):
    def has_message(self):
        pass

    def next_message(self):
        pass

    def append(self, sequence):
        pass


# TODO very inneficient
class LineStreamer(MessageStreamer):
    def __init__(self):
        self.buffer = ""

    def append(self, sequence):
        self.buffer += sequence

    def has_message(self):
        return '\n' in self.buffer

    def next_message(self):
        if not self.has_message():
            return None
        index = self.buffer.index('\n')
        message = self.buffer[:index]
        self.buffer = self.buffer[index+1:]
        return message