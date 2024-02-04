import ctypes

from attrs import define

from hades.rpc.transports.transport import Transport


class HadesProtocolException(Exception):
    pass


class CTypeExtension:
    def __str__(self):
        return "{}: {{{}}}".format(
            self.__class__.__name__,
            ", ".join(
                ["{}: {}".format(field[0], getattr(self, field[0])) for field in self._fields_]
            ),
        )

    def pack(self):
        return ctypes.string_at(ctypes.byref(self), ctypes.sizeof(self))


class HadesRequestHeader(ctypes.LittleEndianStructure, CTypeExtension):
    _pack_ = 1
    _fields_ = [
        ("request", ctypes.c_uint16, 1),
        ("request_id", ctypes.c_uint16, 15),
        ("command", ctypes.c_uint16),
    ]


class HadesResponseHeader(ctypes.LittleEndianStructure, CTypeExtension):
    _pack_ = 1
    _fields_ = [
        ("request", ctypes.c_uint16, 1),
        ("request_id", ctypes.c_uint16, 15),
        ("status", ctypes.c_uint16),
    ]


class HadesRequestVersion(ctypes.LittleEndianStructure, CTypeExtension):
    CMD_ID = 0
    _pack_ = 1
    _fields_ = []


class HadesResponseVersion(ctypes.LittleEndianStructure, CTypeExtension):
    CMD_ID = 0
    _pack_ = 1
    _fields_ = [
        ("major", ctypes.c_uint32, 10),
        ("minor", ctypes.c_uint32, 11),
        ("revision", ctypes.c_uint32, 11),
    ]


class HadesRequestNegotiateSize(ctypes.LittleEndianStructure, CTypeExtension):
    CMD_ID = 1
    _pack_ = 1
    _fields_ = [("proposed_size", ctypes.c_uint32)]


class HadesResponseNegotiateSize(ctypes.LittleEndianStructure, CTypeExtension):
    CMD_ID = 1
    _pack_ = 1
    _fields_ = [("negotiated_size", ctypes.c_uint32)]


class HadesRequestRPC(ctypes.LittleEndianStructure, CTypeExtension):
    CMD_ID = 2
    _pack_ = 1
    _fields_ = [
        ("target", ctypes.c_ubyte * 20),
        ("size", ctypes.c_uint32),
    ]


class HadesResponseRPC(ctypes.LittleEndianStructure, CTypeExtension):
    CMD_ID = 2
    _pack_ = 1
    _fields_ = [("size", ctypes.c_uint32)]


@define
class HadesProtocolVersion:
    major: int
    minor: int
    revision: int


class HadesProtocol:

    def __init__(self, transport: Transport):
        self.transport = transport
        self.request_id = 0
        self.negotiated_size = 1024

    def open(self):
        self.transport.open()

    def close(self):
        self.transport.close()

    def get_version(self) -> HadesProtocolVersion:
        request = HadesRequestVersion()
        response = self._send_request(HadesRequestVersion.CMD_ID, request.pack())

        if len(response) < ctypes.sizeof(HadesResponseVersion):
            raise HadesProtocolException("Malformed response")

        version = HadesResponseVersion.from_buffer(bytearray(response))
        return HadesProtocolVersion(
            major=version.major, minor=version.minor, revision=version.revision
        )

    def negotiate_size(self, proposed_size) -> int:
        request = HadesRequestNegotiateSize(proposed_size=proposed_size)
        response = self._send_request(HadesRequestNegotiateSize.CMD_ID, request.pack())

        if len(response) < ctypes.sizeof(HadesResponseNegotiateSize):
            raise HadesProtocolException("Malformed response")

        negotiated_size = HadesResponseNegotiateSize.from_buffer(bytearray(response))
        self.negotiated_size = negotiated_size.negotiated_size
        return negotiated_size.negotiated_size

    def _send_request(self, command_id: int, request: bytes) -> bytes:
        header = HadesRequestHeader(
            request=1, request_id=self._get_request_id(), command_id=command_id
        )
        self.transport.send(header.pack() + request)
        response = self.transport.receive()

        if len(response) < ctypes.sizeof(HadesResponseHeader):
            raise HadesProtocolException("Malformed response, response is less than expected size")

        response_header = HadesResponseHeader.from_buffer(
            bytearray(response[: ctypes.sizeof(HadesResponseHeader)])
        )

        if response_header.request != 0:
            raise HadesProtocolException("Expected response, received request")

        if response_header.status != 0:
            raise HadesProtocolException(f"Endpoint responded error: {response_header.status}")

        return response[ctypes.sizeof(HadesResponseHeader) :]

    def _get_request_id(self) -> int:
        self.request_id = (self.request_id + 1) & 0xFFFF
        return self.request_id
