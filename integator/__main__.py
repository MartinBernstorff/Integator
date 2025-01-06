import logging
import pathlib
import time

import typer

from integator.git import Git
from integator.git_log import GitLog
from integator.log import log_impl
from integator.settings import FILE_NAME, RootSettings, find_settings_file
from integator.shell import Shell
from integator.task_status_repo import TaskStatusRepo
from integator.watch_impl import CommandRan, watch_impl

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
            print(f"Settings file already exists at: {destination_dir}")
        case None:
            new_path = pathlib.Path.cwd() / FILE_NAME
            settings.write_toml(new_path)
            print(f"Settings file created at: {new_path}")

    gitignore_path = pathlib.Path.cwd() / ".gitignore"
    match gitignore_path.exists():
        case True:
            update_gitignore(gitignore_path)
        case False:
            pass


def update_gitignore(gitignore_path: pathlib.Path):
    if ".logs/" not in gitignore_path.read_text().strip():
        with open(gitignore_path, "a") as f:
            f.write("\n.logs/")
            print("Added .logs to .gitignore")


@app.command("w")
@app.command()
def watch(debug: bool = False):
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
        print(f"Watching {settings.integator.source_dir} for new commits")
        status = watch_impl(
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
