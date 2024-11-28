import pathlib
import time

import typer

from integator.git import Git, Log
from integator.monitor_impl import CommandRan, monitor_impl
from integator.settings import FILE_NAME, RootSettings, settings_file_exists
from integator.shell import Shell

app = typer.Typer()

# TODO: Add monitoring command which runs a verify script


@app.command("i")
@app.command()
def init():
    settings = RootSettings()

    if not settings_file_exists():
        settings.write_toml(pathlib.Path.cwd() / FILE_NAME)

    print("Settings file created")


@app.command("m")
@app.command()
def monitor():
    settings = RootSettings()

    shell = Shell()
    while True:
        shell.clear()

        status = monitor_impl(
            shell,
            git=Git(
                source_dir=settings.integator.source_dir,
                log=Log(expected_cmd_names=settings.cmd_names()),
            ),
        )

        if status == CommandRan.NO:
            time.sleep(1)


@app.command("l")
@app.command()
def log():
    settings = RootSettings()

    git = Git(
        source_dir=settings.integator.source_dir,
        log=Log(settings.cmd_names()),
    )
    shell = Shell()

    while True:
        settings = RootSettings()
        git.print_log()
        shell.clear()
        time.sleep(1)


if __name__ == "__main__":
    app()
