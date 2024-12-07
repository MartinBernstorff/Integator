import datetime
import time

import humanize
from iterpy import Arr
from rich.console import Console
from rich.table import Table

from integator.emojis import Emojis
from integator.git import Commit, Git, Log
from integator.settings import RootSettings
from integator.shell import Shell
from integator.task_status import ExecutionState, Statuses
from integator.task_status_repo import TaskStatusRepo


def _print_status_line(pairs: list[tuple[Commit, Statuses]]):
    print("\n")
    with_failures = Arr(pairs).filter(lambda i: i[1].has_failed())
    if with_failures.count() > 0:
        print(f"{Emojis.FAIL.value} Latest failed: {with_failures[0][0].hash[0:4]}")
        latest_failure = with_failures[0][1].get_failures()[0]
        print(f"\t{latest_failure.log}")
        return

    ok_entries = Arr(pairs).filter(lambda i: i[1].all(ExecutionState.SUCCESS))
    if ok_entries.count() > 0:
        ok_entry = ok_entries[0]
        print(f"{Emojis.OK.value} Latest success: {ok_entry}")
    else:
        print("No commit has passing tests yet")


def print_log(
    entries: list[Commit], task_names: list[str], status_repo: TaskStatusRepo
):
    Shell().clear()

    table = Table(box=None)
    table.add_column("")
    table.add_column("".join([n[0:2] for n in task_names]), justify="center")
    table.add_column("")
    table.add_column("")

    pairs = [(entry, status_repo.get(entry.hash)) for entry in entries]

    for entry, statuses in pairs:
        state_emojis = [statuses.get(cmd).state.__str__() for cmd in task_names]
        table.add_row(
            entry.hash[0:4],
            "".join(state_emojis),
            f"{humanize.naturaldelta(entry.age())} ago",
            statuses.get("Push").state.__str__(),
        )
    Console().print(table)

    _print_status_line(pairs)

    # Print current time
    print(f"\n{datetime.datetime.now().strftime('%H:%M:%S')}")


def log_impl():
    settings = RootSettings()

    git = Git(
        source_dir=settings.integator.source_dir,
        log=Log(set(settings.cmd_names())),
    )

    while True:
        settings = RootSettings()
        commits = git.log.get()
        print_log(commits, settings.cmd_names(), TaskStatusRepo())
        time.sleep(1)
