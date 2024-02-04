import ctypes
from typing import Optional

import serial

from hades.rpc.transports.transport import Transport, TransportException


class SimpleSerialHeader(ctypes.LittleEndianStructure):
    HEADER_MAGIC = 0xF33D10B0
    _pack_ = 1
    _fields_ = [("magic", ctypes.c_uint32), ("size", ctypes.c_uint32)]

    def __init__(self, size):
        self.magic = SimpleSerialHeader.HEADER_MAGIC
        self.size = size

    def pack(self):
        return ctypes.string_at(ctypes.byref(self), ctypes.sizeof(self))


class SimpleSerial(Transport):

    def __init__(self, port: str, baud: int):
        self.port = port
        self.baud = baud
        self.serial: Optional[serial.Serial] = None

    def open(self):
        if self.serial:
            self.close()

        self.serial = serial.Serial(port=self.port, baudrate=self.baud)

    def close(self):
        if self.serial:
            self.serial.close()
            self.serial = None

    def send(self, payload: bytes):
        if not self.serial:
            raise TransportException("Connection has not been opened")

        header = SimpleSerialHeader(len(payload))
        self.serial.write(header.pack() + payload)

    def receive(self) -> bytes:
        if not self.serial:
            raise TransportException("Connection has not been opened")

        read_bytes = self.serial.read(ctypes.sizeof(SimpleSerialHeader))
        response = SimpleSerialHeader.from_buffer(bytearray(read_bytes))
        if response.magic != SimpleSerialHeader.HEADER_MAGIC:
            raise TransportException(f"Bad message expected header, bad magic: {response.magic}")

        return self.serial.read(response.size)
