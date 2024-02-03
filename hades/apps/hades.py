from hades.generator.generator import Generator

import typer
from typing_extensions import Annotated

app = typer.Typer()

@app.callback()
def callback():
    pass

@app.command()
def generate(
    proto_file: Annotated[str, typer.Argument(help="The proto file to use for generator")],
    output_directory: Annotated[str, typer.Argument(help="Directory from where the generated files will be placed")]
):
    """
    Generates a set of c and h files from a proto file. These files can be 
    imported to a c/c++ application in order to implement a hades RPC server
    """
    generator = Generator(
        target_path=proto_file,
        output_directory=output_directory
    ).generate()

if __name__ == "__main__":
    app()