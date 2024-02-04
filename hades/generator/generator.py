import hashlib
import itertools
import os
import pathlib
import sys
from dataclasses import dataclass

import grpc
from google.protobuf import descriptor

from hades.generator.nanopb import NanoPBWrapper


class GeneratorException(Exception):
    pass


@dataclass
class RPC:
    name: str
    id: bytes
    input_type: str
    output_type: str

    def __init__(self, target: descriptor.MethodDescriptor):
        self.name = target.full_name
        self.symbol_name = target.full_name.replace(".", "_")
        self.id = hashlib.sha1(str.encode(self.name)).digest()
        self.input_type = NanoPBWrapper.get_associated_symbol(target.input_type.full_name)
        self.output_type = NanoPBWrapper.get_associated_symbol(target.output_type.full_name)


@dataclass
class Service:
    name: str
    id: bytes
    rpcs: list[RPC]

    def __init__(self, target: descriptor.ServiceDescriptor):
        self.name = target.full_name
        self.symbol_name = target.full_name.replace(".", "_")
        self.id = hashlib.sha1(str.encode(self.name)).digest()
        self.rpcs = []

        for method in target.methods:
            self.rpcs.append(RPC(method))


@dataclass
class ProtoFile:
    name: str
    include_files: set[str]
    services: list[Service]

    def __init__(self, target: descriptor.FileDescriptor):
        self.name = target.name
        self.services = []
        self.include_files = set()
        for service in target.services_by_name.items():
            self.services.append(Service(service[1]))
            for method in service[1].methods:
                self.include_files.add(
                    NanoPBWrapper.get_associated_include(method.output_type.file.name)
                )
                self.include_files.add(
                    NanoPBWrapper.get_associated_include(method.input_type.file.name)
                )


class Generator:

    def __init__(self, target_path: str, output_directory: str):
        self.target_path = target_path
        self.output_directory = output_directory
        self.proto_directory = os.path.dirname(self.target_path)

    def generate(self):
        sys.path.insert(0, self.proto_director)  # Proto needs the files in the path
        os.chdir(self.proto_directory)  # Proto doesn't work well with windows paths
        protos = grpc.protos(os.path.basename(self.target_path))
        files = list(map(lambda x: ProtoFile(x), Generator._resolve_files(protos.DESCRIPTOR)))

        # Generate NanoPB
        for file in files:
            NanoPBWrapper.generate(
                target_path=os.path.join(self.proto_directory, file.name),
                output_directory=self.output_directory,
                proto_directory=self.proto_directory,
            )

        # Generate svc headers
        for file in files:
            self._generate_file(file)

    def _generate_file(self, proto: ProtoFile):

        if len(proto.services) == 0:
            return  # No need for a header

        file_name = os.path.join(
            self.output_directory,
            os.path.dirname(proto.name),
            pathlib.Path(proto.name).stem + ".svc.h",
        )

        with open(file_name, "w") as file:
            file.write("#include <hades.h>\n")

            for include in proto.include_files:
                file.write(f'#include "{include}"\n')

            for service in proto.services:
                for rpc in service.rpcs:
                    file.write(f"void {rpc.symbol_name}(hades_rpc_t* rpc, void* context);\n")

                file.write(
                    "static const __attribute__((unused)) hades_service_descriptor_t "
                    + f"hades_svc_{service.symbol_name} = {{\n"
                )
                file.write(
                    f'\t.id = {{.data={{{",".join(map(lambda x: f"{x:#02x}", service.id))}}}}},\n'
                )
                file.write("\t.rpcs = {\n")
                for rpc in service.rpcs:
                    file.write("\t\t&(hades_rpc_descriptor_t){\n")
                    file.write(
                        "\t\t\t.id = "
                        + f'{{.data={{{",".join(map(lambda x: f"{x:#02x}", rpc.id))}}}}},\n'
                    )
                    file.write(f"\t\t\t.input_msg_descriptor = {rpc.input_type}_fields,\n")
                    file.write(f"\t\t\t.output_msg_descriptor = {rpc.output_type}_fields,\n")
                    file.write(f"\t\t\t.handler = {rpc.symbol_name},\n")
                    file.write("\t\t},\n")
                file.write("\t\tNULL\n")
                file.write("\t}\n")
                file.write("};\n")

    @staticmethod
    def _resolve_files(
        root_descriptor: descriptor.FileDescriptor,
    ) -> set[descriptor.FileDescriptor]:
        files = set()

        files.add(root_descriptor)

        for dependency in itertools.chain(
            root_descriptor.public_dependencies, root_descriptor.dependencies
        ):
            files = files | Generator._resolve_files(dependency)

        return files
