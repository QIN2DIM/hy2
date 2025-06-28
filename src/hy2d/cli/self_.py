import subprocess
from importlib import metadata

import typer

app = typer.Typer(
    name="self",
    help="Manage the anytls-py tool itself.",
    add_completion=False,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    mihomo-anytls-inbound manager
    """
    # 如果没有提供子命令，显示帮助信息
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        ctx.exit(0)


@app.command()
def update():
    """
    Update anytls-py to the latest version.
    """
    try:
        typer.echo("Running `uv tool update anytls-py`...")
        process = subprocess.run(
            ["uv", "tool", "update", "anytls-py"], check=True, capture_output=True, text=True
        )
        typer.echo(process.stdout)
        typer.echo(process.stderr)
        typer.echo("anytls-py updated successfully.")
    except FileNotFoundError:
        typer.echo("Error: `uv` command not found. Please ensure uv is installed and in your PATH.")
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error updating anytls-py:")
        typer.echo(e.stdout)
        typer.echo(e.stderr)
        raise typer.Exit(code=1)


@app.command()
def version():
    """
    Show the version of the anytls-py tool.
    """
    try:
        v = metadata.version("anytls-py")
        typer.echo(f"anytls-py version {v}")
    except metadata.PackageNotFoundError:
        typer.echo("Could not determine version. Is anytls-py installed as a package?")
        raise typer.Exit(code=1)
