import typer

from hades.apps.endpoint import app as endpoint_app
from hades.apps.generator import app as generator_app

app = typer.Typer()

app.add_typer(generator_app, name="generate")
app.add_typer(endpoint_app, name="endpoint")

if __name__ == "__main__":
    app()
