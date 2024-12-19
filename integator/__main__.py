import logging
import pathlib
import time

import typer

from integator.git import Git
from integator.git_log import GitLog
from integator.log import log_impl
from integator.monitor_impl import CommandRan, monitor_impl
from integator.settings import RootSettings, find_settings_file
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

    destination_dir = find_settings_file()
    match destination_dir:
        case pathlib.Path():
            settings.write_toml(destination_dir)
            print(f"Settings file created at: {destination_dir}")
        case None:
            print(f"Settings file already exists at: {destination_dir}")

    gitignore_path = pathlib.Path.cwd() / ".gitignore"
    match gitignore_path.exists():
        case True:
            update_gitignore(gitignore_path)
            print("Added ignores to .gitignore")
        case False:
            pass


def update_gitignore(gitignore_path: pathlib.Path):
    if "integator.toml" not in gitignore_path.read_text().strip():
        with open(gitignore_path, "a") as f:
            f.write("\n.logs/")


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
