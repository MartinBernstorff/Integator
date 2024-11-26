import datetime

import pytest

from integator.emojis import Emojis
from integator.log_entry import LogEntry, Statuses


def test_serde_identity():
    input = f"C|a9c7203| T|16 hours ago| A|Martin Bernstorff| N|[{Emojis.FAIL.value}] P:false|"

    for _ in range(1, 3):
        entry = LogEntry.from_str(input, 1)
        assert entry.__str__() == input
        input = entry.__str__()


@pytest.mark.parametrize(
    "input, n_statuses, expected",
    [
        (
            "C|af7b573| T|5 days ago| A|Martin Bernstorff| N|[G] Test passed|",
            1,
            LogEntry(
                time_since=datetime.timedelta(days=5),
                hash="af7b573",
                author="Martin Bernstorff",
                notes="Test passed",
                statuses=Statuses(values=["G"], size=1),
                pushed=False,
            ),
        ),
        (
            "C|1| T|2 minutes ago| A|Martin Bernstorff| N||",
            1,
            LogEntry(
                time_since=datetime.timedelta(minutes=2),
                hash="1",
                author="Martin Bernstorff",
                notes="",
                statuses=Statuses(values=[Emojis.UNKNOWN.value], size=1),
                pushed=False,
            ),
        ),
        (
            "C|2| T|3 minutes ago| A|Martin Bernstorff| N|P:True|",
            1,
            LogEntry(
                time_since=datetime.timedelta(minutes=3),
                hash="2",
                author="Martin Bernstorff",
                notes="",
                statuses=Statuses(values=[Emojis.UNKNOWN.value], size=1),
                pushed=True,
            ),
        ),
    ],
)
def test_log_entry_parsing(input: str, n_statuses: int, expected: LogEntry):
    parsed = LogEntry.from_str(input, n_statuses)
    assert parsed.__str__() == expected.__str__()


def test_status_setting_from_empty():
    entry = LogEntry(
        time_since=datetime.timedelta(minutes=2),
        hash="123456",
        author="Martin Bernstorff",
        notes="",
        statuses=Statuses(values=[], size=2),
        pushed=False,
    )

    entry.set_ok(0)
    assert entry.statuses.values == [Emojis.OK.value, Emojis.UNKNOWN.value]
