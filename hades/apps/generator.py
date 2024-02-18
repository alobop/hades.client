import typer
from typing_extensions import Annotated

from hades.generator.generator import Generator

app = typer.Typer()


@app.command()
def generate(
    proto_file: Annotated[str, typer.Argument(help="The proto file to use for generator")],
    output_directory: Annotated[
        str,
        typer.Argument(help="Directory from where the generated files will be placed"),
    ],
):
    """
    Generates a set of c and h files from a proto file. These files can be
    imported to a c/c++ application in order to implement a hades RPC server
    """
    Generator(target_path=proto_file, output_directory=output_directory).generate()
