import logging
import pathlib
import time
from functools import partial
from multiprocessing import Process

import typer

from integator.git import Git
from integator.log import log_impl
from integator.settings import FILE_NAME, RootSettings, find_settings_file
from integator.shell import Shell
from integator.task_status_repo import TaskStatusRepo
from integator.watch_impl import CommandRan, watch_impl

logger = logging.getLogger(__name__)
format = "%(asctime)s \t%(levelname)s \t%(name)s \t%(message)s"
date_fmt = "%H:%M:%S"


def init_log(debug: bool, quiet: bool):
    log_level = logging.ERROR if quiet else logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format=format,
        datefmt=date_fmt,
    )


app = typer.Typer()

# refactor: It might make sense to convert these commands to their own files, as
# they seem to be growing. But I'm not sure how to do that with Typer.
# Just importing the app object causes circular imports. Similar problem with routes in
# This would also remove the watch/watch_impl separation, which duplicates a lot of logic.

# I have a few commands I would like to add here.
# feat: A `check` command, which
#   Returns the combined AND state; super useful e.g. in CI.


@app.command("c")
@app.command()
def check(
    hash: str = typer.Option(None, "--hash", help="Commit hash to check"),
    step: str = typer.Option(None, "--step", help="Step to check"),
    debug: bool = False,
    quiet: bool = False,
):
    # Runs all steps for the current commit (default), or for a given commit (--hash argument), or for a given step (--step).
    init_log(debug, quiet)
    settings = RootSettings()

    # ?: How do we handle existing statuses? Just wipe them? Perhaps we want that as an --override option.
    # This depends upon whether the statuses are pushed to remote, I think.
    # By default:
    # * Want to rerun, without modifying status? Then noone is confused by missing status.
    # * Or skip, and output to logs that you can run `clear`?
    # * Perhaps completely separate the implementation of "check" with "run"?

    # Should this perhaps share implementation with watch? I think so, very much!

    # If hash is specified, do fuzzy matching to get a given commit. Otherwise, just get the latest one.

    # If step is specified, only run that one, otherwise, run all.


# feat: A `check` command, which checks the combined status of all (default) or one (--step), for latest or a given commit (--hash)

#
# feat: A `clear` command, which removes all step states for a given commit. By default, removes for the latest commit.

# ?: We do not want to use an existing DAG tool as the job-engine, because that makes it very hard to get task status,
# and therefore how to present it nicely and log it to persistence.


@app.command("i")
@app.command()
def init():
    settings = RootSettings()

    # feat: add a selector here, to choose from existing files in ~/.config/integator/templates
    # Then we can have e.g. a Python.toml template, which can be used as a starting point.
    # Perhaps we want merging of the default with whichever settings are specified in the template?
    # This means we can
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
    init_log(debug, quiet)

    settings = RootSettings()

    shell = Shell()
    while True:
        if not debug:
            shell.clear()

        logger.debug("--- Init'ing ---")
        git = Git(source_dir=settings.integator.source_dir)

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
def tui(debug: bool = False, quiet: bool = False):
    init_log(debug, quiet)
    from integator.tui.main import IntegatorTUI

    side_process = Process(target=partial(watch, debug, quiet=True), daemon=True)
    side_process.start()

    app = IntegatorTUI()
    app.run()


@app.command("l")
@app.command()
def log(debug: bool = False, quiet: bool = False):
    init_log(debug, quiet)
    log_impl(debug)


if __name__ == "__main__":
    app()
