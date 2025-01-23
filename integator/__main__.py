import logging
import pathlib
import time
from functools import partial
from multiprocessing import Process

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
def watch(debug: bool = False, quiet: bool = False):
    log_level = logging.ERROR if quiet else logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
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
        logger.info(
            f"Integator {settings.version()}: Watching {settings.integator.source_dir} for new commits"
        )
        status = watch_impl(
            shell,
            source_git=git,
            status_repo=TaskStatusRepo(),
            quiet=quiet,
        )

        logger.debug("--- Sleeping ---")
        if status == CommandRan.NO:
            time.sleep(1)


@app.command("t")
@app.command()
def tui(debug: bool = False):
    from integator.tui.main import IntegatorTUI

    side_process = Process(target=partial(watch, debug, quiet=True), daemon=True)
    side_process.start()

    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format=format,
            datefmt=date_fmt,
        )

    app = IntegatorTUI()
    app.run()


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
