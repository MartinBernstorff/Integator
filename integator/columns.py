import datetime

import humanize
from iterpy import Arr

from integator.commit import Commit
from integator.git import Git
from integator.settings import IntegatorSettings
from integator.step_status import Statuses

# refactor: do I want to remove logging completely? Or at least dramatically simplify it.
# More akin to git log, to output something in e.g. CI. For fancy functionality, we want
# to use the TUI.


def status(pairs: list[tuple[Commit, Statuses]], step_names: list[str]) -> list[str]:
    return (
        Arr(pairs)
        .map(lambda pair: status_row(pair, step_names))
        .map(lambda statuses: "".join(statuses))
        .to_list()
    )


def status_row(pair: tuple[Commit, Statuses], step_names: list[str]) -> list[str]:
    return [pair[1].get(cmd).state.__str__() for cmd in step_names]


def age(pair: tuple[Commit, Statuses]) -> str:
    age = pair[0].age()
    return (
        f"{humanize.naturaldelta(age)} ago"
        if age > datetime.timedelta(minutes=1)
        else "< 1 minute"
    )


def progress_bar(filled: int, total: int, threshold: int | None = None) -> str:
    if filled >= total:
        return "█" * total

    empty_length = total - filled
    elements: list[str] = []

    elements.extend(["█" for _ in range(filled)])
    elements.extend(["░" for _ in range(empty_length)])

    if threshold is not None:
        elements.insert(threshold, "|")

    return "".join(elements)


def duration(pair: tuple[Commit, Statuses]) -> str:
    return humanize.naturaldelta(pair[1].duration())


def complexity(
    pair: tuple[Commit, Statuses], git: Git, settings: IntegatorSettings
) -> str:
    entry = pair[0]
    change_count = git.change_count(entry.hash)
    total_count = change_count.insertions + change_count.deletions
    change_complexity = total_count + change_count.files

    return progress_bar(
        filled=int(change_complexity / settings.complexity_changes_per_block),
        total=int(settings.complexity_bar_max / settings.complexity_changes_per_block),
        threshold=int(
            settings.complexity_threshold / settings.complexity_changes_per_block
        ),
    )
