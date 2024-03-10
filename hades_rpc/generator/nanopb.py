import os
import pathlib
import subprocess
import sys
from typing import Optional

import nanopb


class NanoPBException(Exception):
    pass


class NanoPBWrapper:

    @staticmethod
    def generate(target_path: str, output_directory: str, proto_directory: Optional[str] = None):
        nanopb_generator = os.path.join(nanopb.__path__[0], "generator/nanopb_generator")
        result = subprocess.run(
            [
                sys.executable,
                nanopb_generator,
                f"--proto-path={proto_directory}",
                f"--output-dir={output_directory}",
                target_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise NanoPBException(f"nanopb failed with {result.returncode}: \n{result.stdout}")

    @staticmethod
    def get_associated_include(proto_path: str) -> str:
        return str(
            os.path.join(os.path.dirname(proto_path), f"{pathlib.Path(proto_path).stem}.pb.h")
        )

    @staticmethod
    def get_associated_symbol(symbol: str) -> str:
        return symbol.replace(".", "_")
