import importlib
import re
import sys
from typing import Any

import typer
from typing_extensions import Annotated

from hades.rpc.protocol import HadesEndpoint

app = typer.Typer()

state = {}


def parse_connection(connection_string: str) -> Any:
    result = re.search(r"(.+)\.(.+)\((.*)\)", connection_string)

    if not result:
        raise Exception(f'Unable to parse connection string: {str}')

    import_path = result.group(1)
    class_name = result.group(2)
    params = dict(item.split("=") for item in result.group(3).split(","))

    module = importlib.import_module(f"hades.rpc.transports.{import_path}")
    target_class = getattr(module, class_name)

    return target_class(**params)


@app.callback()
def endpoint(
    connection: Annotated[
        int,
        typer.Option(
            parser=parse_connection,
            help="Connection string for the target endpoint",
            envvar="HADES_CONNECTION",
        ),
    ]
):
    """
    Interacts with a given endpoint
    """
    if not connection:
        raise Exception("Connection was not given")

    state["connection"] = connection


@app.command()
def query_version():
    with HadesEndpoint(state["connection"]) as endpoint:
        print(endpoint.get_version())


@app.command()
def query_message_size():
    with HadesEndpoint(state["connection"]) as endpoint:
        print(endpoint.negotiate_size(sys.maxsize))
