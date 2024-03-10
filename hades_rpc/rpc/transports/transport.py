class TransportException(Exception):
    pass


class Transport:
    def open(self):
        pass

    def close(self):
        pass

    def receive(self) -> bytes:
        return b""

    def send(self, payload: bytes):
        pass
