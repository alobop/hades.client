import importlib
import re
from typing import Any

import typer
from typing_extensions import Annotated

from hades.rpc.rpc import Hades

app = typer.Typer()

state = {}


def parse_connection(connection_string: str) -> Any:
    result = re.search(r"(.+)\.(.+)\((.*)\)", connection_string)

    if not result:
        raise Exception(f"Unable to parse connection string: {str}")

    import_path = result.group(1)
    class_name = result.group(2)
    params = dict(item.split("=") for item in result.group(3).split(","))

    module = importlib.import_module(f"hades.rpc.transports.{import_path}")
    target_class = getattr(module, class_name)

    return target_class(**params)


@app.callback()
def endpoint(
    proto: Annotated[
        str,
        typer.Option(
            help="Proto file that defines the service interface",
            envvar="HADES_SERVICE_DEFINITION",
        ),
    ]
):
    state["service_definition"] = proto


@app.command()
def list():
    print(Hades(state["service_definition"]).describe(), end="")
