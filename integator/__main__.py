import logging
import pathlib
import time

import typer

from integator.git import Git
from integator.git_log import GitLog
from integator.log import log_impl
from integator.monitor_impl import CommandRan, monitor_impl
from integator.settings import FILE_NAME, RootSettings, settings_file_exists
from integator.shell import Shell
from integator.task_status_repo import TaskStatusRepo

logger = logging.getLogger(__name__)
format = "%(asctime)s \t%(levelname)s \t%(name)s \t%(message)s"
date_fmt = "%H:%M:%S"

app = typer.Typer()


@app.command("i")
@app.command()
def init():
    settings = RootSettings()

    if not settings_file_exists():
        settings.write_toml(pathlib.Path.cwd() / FILE_NAME)

    print("Settings file created")


@app.command("m")
@app.command()
def monitor(debug: bool = False):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.ERROR,
        format=format,
        datefmt=date_fmt,
    )

    settings = RootSettings()

    shell = Shell()
    while True:
        if not debug:
            shell.clear()

        logger.debug("--- Init'ing ---")
        # XXX: Create the worktree in a temporary dir
        git = Git(
            source_dir=settings.integator.source_dir,
            log=GitLog(),
        )

        logger.debug("Running")
        print(f"Monitoring {settings.integator.source_dir} for new commits")
        status = monitor_impl(
            shell,
            source_git=git,
            status_repo=TaskStatusRepo(),
        )

        logger.debug("--- Sleeping ---")
        if status == CommandRan.NO:
            time.sleep(1)


@app.command("l")
@app.command()
def log(debug: bool = False):
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format=format,
            datefmt=date_fmt,
        )
    log_impl(debug)


if __name__ == "__main__":
    app()
