import datetime
import logging
import time
from dataclasses import dataclass
from typing import Callable

import humanize
from iterpy import Arr
from rich.console import Console
from rich.table import Table

from integator.columns import age, complexity, duration, progress_bar, status
from integator.commit import Commit
from integator.emojis import Emojis
from integator.git import Git
from integator.git_log import GitLog
from integator.settings import IntegatorSettings, RootSettings
from integator.shell import Shell
from integator.task_status import ExecutionState, Statuses
from integator.task_status_repo import TaskStatusRepo

log = logging.getLogger(__name__)


def _last_status_commit(
    pairs: list[tuple[Commit, Statuses]], task_names: set[str]
) -> str:
    with_failures = Arr(pairs).filter(lambda i: i[1].has_failed())
    if with_failures.count() > 0:
        fail_line = (
            f"{Emojis.FAIL.value} Latest failed: {with_failures[0][0].hash[0:4]}"
        )
        latest_failure = with_failures[0][1].get_failures()[0]
        log_line = f"\t{latest_failure.log}"
        return f"{fail_line}\n{log_line}"

    ok_entries = Arr(pairs).filter(
        lambda i: i[1].all(task_names, ExecutionState.SUCCESS)
    )
    if ok_entries.count() > 0:
        ok_entry = ok_entries[0]
        return f"{Emojis.OK.value} Latest success: {ok_entry[0].hash[0:4]}"
    else:
        return "No commit has passing tests yet"


@dataclass
class Column:
    label: str
    title: str
    func: Callable[[list[tuple[Commit, Statuses]]], list[str]]

    def apply(self, pairs: list[tuple[Commit, Statuses]]) -> list[str]:
        return self.func(pairs)


def _print_table2(cols: list[Column], pairs: list[tuple[Commit, Statuses]]):
    table = Table(box=None)

    col_values = [col.apply(pairs) for col in cols]
    for col in cols:
        table.add_column(col.title)

    # Transpose the col_values
    rows = list(zip(*col_values))

    for row in rows:
        table.add_row(*row)

    Console().print(table)


# XXX: This function could take a list of columns instead.
def _print_table(  # type: ignore
    task_names: list[str],
    pairs: list[tuple[Commit, Statuses]],
    git: Git,
    settings: IntegatorSettings,
):
    table = Table(box=None)
    table.add_column("")
    table.add_column("".join([n[0:2] for n in task_names]), justify="center")
    table.add_column("")
    # table.add_column("Change age")
    table.add_column("🤡")
    table.add_column("∆C")
    table.add_column("Task ⌛")
    table.add_column("")

    for entry, statuses in pairs:
        state_emojis = [statuses.get(cmd).state.__str__() for cmd in task_names]

        change_count = git.change_count(entry.hash)
        total_count = change_count.insertions + change_count.deletions
        change_complexity = total_count + change_count.files

        table.add_row(
            f"{entry.hash[0:4]}",
            "".join(state_emojis),
            f"{humanize.naturaldelta(entry.age())} ago"
            if entry.age() > datetime.timedelta(minutes=1)
            else "< 1 min ago",
            progress_bar(
                filled=int(change_complexity / settings.complexity_changes_per_block),
                total=int(
                    settings.complexity_bar_max / settings.complexity_changes_per_block
                ),
                threshold=int(
                    settings.complexity_threshold
                    / settings.complexity_changes_per_block
                ),
            ),
            str(change_complexity),
            f"{humanize.naturaldelta(statuses.duration())}",
            "🌥️" if statuses.get("Push").state == ExecutionState.SUCCESS else "️",
        )
    Console().print(table)


def _ready_for_changes(
    pairs: list[tuple[Commit, Statuses]], task_names: set[str]
) -> bool:
    maybe_latest_passing_commit = (
        Arr(pairs)
        .filter(lambda i: i[1].all_succeeded(task_names))
        .map(lambda it: it[0])
    )

    if maybe_latest_passing_commit.count() == 0:
        log.info("No commit has passing tests yet")
        return False

    latest_passing_commit = maybe_latest_passing_commit.to_list()[0]

    if latest_passing_commit.hash == pairs[0][0].hash:
        log.info("No commit has failed yet")
        return True

    latest_passing_commit_index = None
    for idx, pair in enumerate(pairs):
        if pair[1].all_succeeded(task_names):
            latest_passing_commit_index = idx
            break

    latest_failing_commit_index = None
    for idx, pair in enumerate(pairs):
        if pair[1].has_failed():
            latest_failing_commit_index = idx
            break

    if latest_failing_commit_index is None or latest_passing_commit_index is None:
        log.info("Either no failure or no success yet")
        return False

    if (
        datetime.datetime.now() - latest_passing_commit.timestamp
        < datetime.timedelta(minutes=15)
        and not latest_failing_commit_index < latest_passing_commit_index
    ):
        log.info("No failures for the last 15 minutes")
        return True

    return False


def _print_ready_status(ready: bool):
    line_length = 28
    if ready:
        print(Emojis.OK.value * line_length)
    else:
        print(Emojis.RED.value * line_length)


def log_impl(debug: bool):
    settings = RootSettings()

    git = Git(
        source_dir=settings.integator.source_dir,
        log=GitLog(),
    )

    while True:
        settings = RootSettings()
        commits = git.log.get(8)
        if not debug:
            Shell().clear()

        pairs = [(entry, TaskStatusRepo().get(entry.hash)) for entry in commits]

        _print_ready_status(_ready_for_changes(pairs, set(settings.task_names())))
        _print_table2(
            [
                Column("Hash", "", lambda pairs: [r[0].hash[0:4] for r in pairs]),
                Column(
                    "Statuses",
                    "".join([n[0:2] for n in settings.task_names()]),
                    lambda pairs: status(pairs, settings.task_names()),
                ),
                Column(
                    label="Age",
                    title="",
                    func=lambda pairs: [age(p) for p in pairs],
                ),
                Column(
                    label="🤡",
                    title="",
                    func=lambda pairs: [
                        complexity(p, git, settings.integator) for p in pairs
                    ],
                ),
                Column(
                    label="Duration",
                    title="🕒",
                    func=lambda pairs: [duration(p) for p in pairs],
                ),
            ],
            pairs,
        )
        # _print_table(settings.task_names(), pairs, git, settings.integator)
        now = f"\n{datetime.datetime.now().strftime('%H:%M:%S')}"
        print(f"{now} | {_last_status_commit(pairs, set(settings.task_names()))}")

        time.sleep(0.3)
