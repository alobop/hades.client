import typer

from hades_rpc.apps.endpoint import app as endpoint_app
from hades_rpc.apps.generator import app as generator_app
from hades_rpc.apps.rpc import app as rpc_app

app = typer.Typer()

app.add_typer(generator_app, name="generate")
app.add_typer(endpoint_app, name="endpoint")
app.add_typer(rpc_app, name="rpc")

if __name__ == "__main__":
    app()
