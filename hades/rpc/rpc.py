import grpc
import os
import itertools
import subprocess
import nanopb
import pathlib
from dataclasses import dataclass
import hashlib
import sys
from functools import partial

from hades.rpc.protocol import HadesProtocol, HadesProtocolVersion
from hades.rpc.transports.transport import Transport


class HadesException(Exception):
    pass


class Hades:

    HADES_VERSION = HadesProtocolVersion(major=0, minor=1, revision=5)

    def __init__(self, connection: Transport, proto_path: str, proposed_size: int = 1024):
        self.protocol = HadesProtocol(connection)
        self.proposed_size = proposed_size

        proto_path = os.path.abspath(proto_path)
        sys.path.insert(0, os.path.dirname(proto_path))  # Proto needs the files in the path
        os.chdir(os.path.dirname(proto_path))  # Proto doesn't work well with windows paths
        self.protos = grpc.protos(os.path.basename(proto_path))

    def connect(self) -> object:
        self.protocol.open()

        version = self.protocol.get_version()

        if version.major != Hades.HADES_VERSION.major:
            raise HadesException("Endpoint version is not supported: {version}")

        self.protocol.negotiate_size(self.proposed_size)

        return self._generate_service_tree()

    def _generate_service_tree(self) -> object:
        root = Hades._create_node("root")

        files = Hades._resolve_files(self.protos.DESCRIPTOR)

        for file in files:
            for message in file.message_types_by_name.values():
                Hades._insert_message(root, message)

            for service in file.services_by_name.values():
                for method in service.methods:
                    Hades._insert_method(root, self.protocol, method)

        return root

    @staticmethod
    def _create_node(name: str) -> object:
        return type(name, (object,), {"name": name})

    @staticmethod
    def _insert_message(root, message):
        package_hops = message.full_name.split(".")[:-1]
        current = root

        for package in package_hops:
            if not hasattr(current, package):
                node = Hades._create_node(package)
                setattr(current, package, node)
            current = getattr(current, package)

        setattr(current, message.name, message._concrete_class)

    @staticmethod
    def _insert_method(root, protocol, method):
        package_hops = method.full_name.split(".")[:-1]
        current = root

        for package in package_hops:
            if not hasattr(current, package):
                node = Hades._create_node(package)
                setattr(current, package, node)
            current = getattr(current, package)

        method_id = hashlib.sha1(str.encode(method.full_name)).digest()
        setattr(
            current,
            method.name,
            partial(
                Hades._send_rpc,
                protocol=protocol,
                id=method_id,
                input_type=method.input_type._concrete_class,
                output_type=method.output_type._concrete_class,
            ),
        )

    @staticmethod
    def _resolve_files(target):
        files = set()

        files.add(target)

        for dependency in itertools.chain(target.public_dependencies, target.dependencies):
            files = files | Hades._resolve_files(dependency)

        return files

    @staticmethod
    def _send_rpc(protocol, id, input_type, output_type, **kwargs):
        request = input_type(**kwargs)
        raw_response = protocol.send_rpc(id, request.SerializeToString())
        parsed = output_type()
        parsed.ParseFromString(raw_response)
        return parsed
