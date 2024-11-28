import datetime
import re
from typing import Any

import pytimeparse  # type: ignore

from integator.emojis import Emojis


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


def _find_statuses(notes: str) -> str:
    regex = r"\[.+\]"
    match = re.search(regex, notes)
    if not match:
        return ""
    return match.group(0)


def _pushed(notes: str) -> bool:
    if "P:True" in notes:
        return True
    return False


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
        result: str = match.group(1)

        if name == "time":
            seconds = pytimeparse.parse(result)  # type: ignore

            if seconds is None:
                raise ValueError(f"Invalid time: {result}")

            results[name] = datetime.timedelta(seconds=seconds)
        elif name == "notes":
            results["statuses"] = _statuses(result, n_statuses)
            results["pushed"] = _pushed(result)
            notes = (
                result.replace(_find_statuses(result), "")
                .replace(f"P:{results['pushed']}", "")
                .strip()
            )
            results[name] = notes
        else:
            results[name] = result if match else ""

    return results  # type: ignore
