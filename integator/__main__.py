import logging
import pathlib
import time

import typer

from integator.git import Git, Log
from integator.log import log_impl
from integator.monitor_impl import CommandRan, monitor_impl
from integator.settings import FILE_NAME, RootSettings, settings_file_exists
from integator.shell import Shell
from integator.task_status_repo import TaskStatusRepo

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s \t%(levelname)s \t%(name)s \t%(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

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

        logger.debug("Init'ing")
        git = Git(
            source_dir=settings.integator.source_dir,
            log=Log(expected_cmd_names=set(settings.cmd_names())),
        )

        logger.debug("Running")
        status = monitor_impl(
            shell,
            git=git,
            status_repo=TaskStatusRepo(),
        )

        logger.debug("Sleeping")
        if status == CommandRan.NO:
            time.sleep(1)


@app.command("l")
@app.command()
def log():
    log_impl()


if __name__ == "__main__":
    log()
