"""heyhy 服务管理脚本 - 主入口"""

from importlib import metadata

import typer

from hy2d.cli import install, log, remove, start, stop, update, check, self_
from hy2d.logging_config import setup_logging

app = typer.Typer(
    name="heyhy",
    help="mihomo-hysteria2-inbound manager",
    add_completion=False,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    mihomo-hysteria2-inbound manager
    """
    setup_logging()

    # 如果没有提供子命令，显示帮助信息
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        ctx.exit(0)


@app.command()
def version():
    """
    Show the version of the heyhy tool.
    """
    try:
        v = metadata.version("heyhy")
        typer.echo(f"heyhy version {v}")
    except metadata.PackageNotFoundError:
        typer.echo("Could not determine version. Is heyhy installed as a package?")
        raise typer.Exit(code=1)


# 注册子命令
app.add_typer(self_.app, name="self")
app.add_typer(install.app, name="install")
app.add_typer(remove.app, name="remove")
app.add_typer(log.app, name="log")
app.add_typer(start.app, name="start")
app.add_typer(stop.app, name="stop")
app.add_typer(update.app, name="update")
app.add_typer(check.app, name="check")

if __name__ == "__main__":
    app()
