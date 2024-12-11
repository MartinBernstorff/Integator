import datetime
import logging
import time

import humanize
from iterpy import Arr
from rich.console import Console
from rich.table import Table

from integator.commit import Commit
from integator.emojis import Emojis
from integator.git import Git
from integator.git_log import GitLog
from integator.settings import RootSettings
from integator.shell import Shell
from integator.task_status import ExecutionState, Statuses
from integator.task_status_repo import TaskStatusRepo

log = logging.getLogger(__name__)


def _progress_bar(filled: int, total: int, threshold: int | None = None) -> str:
    if filled >= total:
        return "█" * total

    empty_length = total - filled
    elements = []

    elements.extend(["█" for _ in range(filled)])
    elements.extend(["░" for _ in range(empty_length)])

    if threshold is not None:
        elements.insert(threshold, "|")

    return "".join(elements)


def _print_last_status_commit(
    pairs: list[tuple[Commit, Statuses]], task_names: set[str]
):
    with_failures = Arr(pairs).filter(lambda i: i[1].has_failed())
    if with_failures.count() > 0:
        print(f"{Emojis.FAIL.value} Latest failed: {with_failures[0][0].hash[0:4]}")
        latest_failure = with_failures[0][1].get_failures()[0]
        print(f"\t{latest_failure.log}")
        return

    ok_entries = Arr(pairs).filter(
        lambda i: i[1].all(task_names, ExecutionState.SUCCESS)
    )
    if ok_entries.count() > 0:
        ok_entry = ok_entries[0]
        print(f"{Emojis.OK.value} Latest success: {ok_entry[0].hash[0:4]}")
    else:
        print("No commit has passing tests yet")


# XXX: This function could take a list of columns instead.
def _print_table(task_names: list[str], pairs: list[tuple[Commit, Statuses]], git: Git):
    table = Table(box=None)
    table.add_column("")
    table.add_column("".join([n[0:2] for n in task_names]), justify="center")
    table.add_column("")
    # table.add_column("Change age")
    table.add_column("🤡")
    table.add_column("∆C")
    table.add_column("Task ⌛")
    table.add_column("")

    for idx, (entry, statuses) in enumerate(pairs):
        state_emojis = [statuses.get(cmd).state.__str__() for cmd in task_names]

        # n_blocks_since_last_commit = 0
        # if idx < len(pairs) - 1:
        #     current = pairs[idx][0].timestamp
        #     prior = pairs[idx + 1][0].timestamp
        #     time_since_last_commit = current - prior

        #     if time_since_last_commit.total_seconds() > 5 * 60 * 60:
        #         # Above threshold, probably didn't work on it in this interval
        #         n_blocks_since_last_commit = 0
        #     else:
        #         minutes_per_block = 5
        #         n_blocks_since_last_commit = int(
        #             time_since_last_commit.total_seconds() / 60 / minutes_per_block
        #         )

        change_count = git.change_count(entry.hash)
        total_count = change_count.insertions + change_count.deletions
        change_complexity = total_count + change_count.files

        table.add_row(
            f"{entry.hash[0:4]}",
            "".join(state_emojis),
            f"{humanize.naturaldelta(entry.age())} ago",
            _progress_bar(filled=int(change_complexity / 5), total=10, threshold=2),
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
        commits = git.log.get()
        if not debug:
            Shell().clear()

        pairs = [(entry, TaskStatusRepo().get(entry.hash)) for entry in commits]

        _print_ready_status(_ready_for_changes(pairs, set(settings.task_names())))
        print("")
        _print_table(settings.task_names(), pairs, git)
        print("")
        _print_last_status_commit(pairs, set(settings.task_names()))

        # Print current time
        print(f"\n{datetime.datetime.now().strftime('%H:%M:%S')}")

        time.sleep(1)
