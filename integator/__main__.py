import datetime
import logging
import pathlib
import time

import humanize
import typer
from rich.console import Console
from rich.table import Table

from integator.git import Git, Log
from integator.monitor_impl import CommandRan, monitor_impl
from integator.settings import FILE_NAME, RootSettings, settings_file_exists
from integator.shell import Shell
from integator.task_status import Commit

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
        # shell.clear()

        logger.debug("Init'ing")
        git = Git(
            source_dir=settings.integator.source_dir,
            log=Log(expected_cmd_names=set(settings.cmd_names())),
        )

        logger.debug("Running")
        status = monitor_impl(
            shell,
            git=git,
        )

        logger.debug("Sleeping")
        if status == CommandRan.NO:
            time.sleep(1)


@app.command("l")
@app.command()
def log():
    def print_log(entries: list[Commit], task_names: list[str]):
        Shell().clear()

        table = Table(box=None)
        table.add_column("")
        table.add_column("".join([n[0:2] for n in task_names]), justify="center")
        table.add_column("")

        for entry in entries:
            statuses = [entry.statuses.get(cmd).state.__str__() for cmd in task_names]
            table.add_row(
                entry.hash[0:4],
                "".join(statuses),
                f"{humanize.naturaldelta(entry.age())} ago",
            )
        Console().print(table)

        _print_status_line(entries)
        print("Testing")

        # Print current time
        print(f"\n{datetime.datetime.now().strftime('%H:%M:%S')}")

    def _print_status_line(entries: list[Commit]):
        ok_entries = [entry for entry in entries if entry.all_ok()]
        if ok_entries:
            ok_entry = ok_entries[-1]
            print(f"Last commit passing tests:\n\t{ok_entry}")
        else:
            print("No commit has passing tests yet")

    settings = RootSettings()

    git = Git(
        source_dir=settings.integator.source_dir,
        log=Log(set(settings.cmd_names())),
    )

    while True:
        settings = RootSettings()
        commits = git.log.get()
        print_log(commits, settings.cmd_names())
        time.sleep(1)


if __name__ == "__main__":
    app()
