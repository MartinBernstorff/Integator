import datetime
import re
from typing import Any

import pytimeparse

from integator.cons import Emojis


@staticmethod
def _statuses(notes: str, n_statuses: int) -> list[str]:
    regex = r"\[.+\]"
    match = re.search(regex, notes)
    if not match:
        return []
    icons = match.group(0).strip("[]")

    missing_statuses = n_statuses - len(icons)
    if missing_statuses > 0:
        icons += Emojis.UNKNOWN.value * missing_statuses

    return [c for c in icons]


def _notes_sans_statuses(notes: str) -> str:
    regex = r"\[.+\]"
    match = re.search(regex, notes)
    if not match:
        return notes
    return notes.replace(match.group(0), "").strip()


def _pushed(notes: str) -> bool:
    regex = r"P:true"
    match = re.search(regex, notes)
    return match is not None


def parse_commit(line: str, n_statuses: int) -> dict[str, Any]:
    regexes = [
        ("commit", r"^C\|(.*?)\|"),
        ("time", r"T\|(.*?)\s+ago\|"),
        ("author", r"A\|(.*?)\|"),
        ("notes", r"N\|(.*?)\|"),
    ]

    results = {}

    for name, regex in regexes:
        match = re.search(regex, line)

        if name == "time":
            seconds = pytimeparse.parse(match.group(1))

            if seconds is None:
                raise ValueError(f"Invalid time: {match.group(1)}")

            results[name] = datetime.timedelta(seconds=seconds)
        elif name == "notes":
            results[name] = _notes_sans_statuses(match.group(1))
            results["statuses"] = _statuses(match.group(1), n_statuses)
            results["pushed"] = _pushed(match.group(1))
        else:
            results[name] = match.group(1) if match else ""

    return results
