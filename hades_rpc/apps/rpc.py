import importlib
import json
import re
from typing import Any

import typer
from google.protobuf.json_format import MessageToJson
from typing_extensions import Annotated

from hades_rpc.rpc.rpc import Hades, HadesRPCEndpoint

app = typer.Typer()

state = {}


def parse_connection(connection_string: str) -> Any:
    result = re.search(r"(.+)\.(.+)\((.*)\)", connection_string)

    if not result:
        raise Exception(f"Unable to parse connection string: {str}")

    import_path = result.group(1)
    class_name = result.group(2)
    params = dict(item.split("=") for item in result.group(3).split(","))

    module = importlib.import_module(f"hades_rpc.rpc.transports.{import_path}")
    target_class = getattr(module, class_name)

    return target_class(**params)


@app.callback()
def rpc(
    proto: Annotated[
        str,
        typer.Option(
            help="Proto file that defines the service interface",
            envvar="HADES_SERVICE_DEFINITION",
        ),
    ]
):
    """
    Command set to invoke rpc methods on remote endpoint
    """
    state["service_definition"] = proto


@app.command()
def list():
    """
    Lists the available services and methods
    """
    print(Hades(state["service_definition"]).describe(), end="")


@app.command()
def exec(
    connection: Annotated[
        Any,
        typer.Option(
            parser=parse_connection,
            help="Connection string for the target endpoint",
            envvar="HADES_CONNECTION",
        ),
    ],
    method: Annotated[str, typer.Argument(help="Method to invoke")],
    args: Annotated[str, typer.Argument(help="Args in json format to pass the method")],
):
    with HadesRPCEndpoint(proto=state["service_definition"], transport=connection) as hades:
        hops = method.split(".")
        target_method = hades

        for hop in hops:
            target_method = getattr(target_method, hop)

        data = json.loads(args)
        print(MessageToJson(target_method(**data)))
