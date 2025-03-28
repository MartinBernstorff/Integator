import datetime
import logging
import time
from dataclasses import dataclass
from typing import Callable

from iterpy import Arr
from rich.console import Console
from rich.table import Table

from integator.columns import age, duration, status
from integator.commands.argument_parsing import get_settings, template_defaults
from integator.commit import Commit
from integator.emojis import Emojis
from integator.git import Git
from integator.shell import Shell
from integator.step_status import ExecutionState, Statuses
from integator.step_status_repo import StepStatusRepo

log = logging.getLogger(__name__)


def _last_status_commit(
    pairs: list[tuple[Commit, Statuses]], step_names: set[str]
) -> str:
    with_failures = Arr(pairs).filter(lambda i: i[1].has_failed())
    if with_failures.len() > 0:
        fail_line = (
            f"{Emojis.FAIL.value} Latest failed: {with_failures[0][0].hash[0:4]}"
        )
        latest_failure = with_failures[0][1].get_failures()[0]

        if latest_failure.log is not None:
            log_line = f"{latest_failure.log}"
            log_lines = latest_failure.log.read_text().split("\n")

            n_lines = 10
            lines_in_log = len(log_lines)
            excerpted_lines = (
                log_lines[-n_lines:]
                if lines_in_log >= n_lines
                else log_lines[-lines_in_log:]
            )

            excerpt = "\n\t".join(excerpted_lines)

            return f"""{fail_line}
        {log_line}

Excerpt:
{excerpt}"""

    ok_entries = Arr(pairs).filter(
        lambda i: i[1].all(step_names, ExecutionState.SUCCESS)
    )
    if ok_entries.len() > 0:
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


def _ready_for_changes(
    pairs: list[tuple[Commit, Statuses]], step_names: set[str]
) -> bool:
    maybe_latest_passing_commit = (
        Arr(pairs)
        .filter(lambda i: i[1].all_succeeded(step_names))
        .map(lambda it: it[0])
    )

    if maybe_latest_passing_commit.len() == 0:
        log.info("No commit has passing tests yet")
        return False

    latest_passing_commit = maybe_latest_passing_commit.to_list()[0]

    if latest_passing_commit.hash == pairs[0][0].hash:
        log.info("No commit has failed yet")
        return True

    latest_passing_commit_index = None
    for idx, pair in enumerate(pairs):
        if pair[1].all_succeeded(step_names):
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


def log_impl(debug: bool, template_name: str | None = template_defaults):
    settings = get_settings(template_name)

    git = Git(source_dir=settings.integator.root_worktree_dir)

    while True:
        settings = get_settings(template_name)
        commits = git.log.get(8)
        if not debug:
            Shell().clear()

        pairs = [(entry, StepStatusRepo().get(entry.hash)) for entry in commits]

        print(f"Integator {settings.version()}")
        _print_ready_status(_ready_for_changes(pairs, set(settings.step_names())))
        _print_table2(
            [
                Column("Hash", "", lambda pairs: [r[0].hash[0:5] for r in pairs]),
                Column(
                    "Statuses",
                    "".join([n[0:2] for n in settings.step_names()]),
                    lambda pairs: status(pairs, settings.step_names()),
                ),
                Column(
                    label="Age",
                    title="",
                    func=lambda pairs: [age(p) for p in pairs],
                ),
                Column(
                    label="Duration",
                    title="🕒",
                    func=lambda pairs: [duration(p) for p in pairs],
                ),
            ],
            pairs,
        )
        # _print_table(settings.step_names(), pairs, git, settings.integator)
        now = f"\n{datetime.datetime.now().strftime('%H:%M:%S')}"
        print(f"{now} | {_last_status_commit(pairs, set(settings.step_names()))}")

        time.sleep(0.3)
