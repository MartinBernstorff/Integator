import datetime

import pytest

from integator.log_entry import LogEntry, Statuses


def test_serde_identity():
    input = "C|a9c7203| T|16 hours ago| A|Martin Bernstorff| N|[?]|"

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
            ),
        ),
        (
            "C|123456| T|2 minutes ago| A|Martin Bernstorff| N||",
            1,
            LogEntry(
                time_since=datetime.timedelta(minutes=2),
                hash="123456",
                author="Martin Bernstorff",
                notes="",
                statuses=Statuses(values=["?"], size=1),
            ),
        ),
        (
            "C|123456| T|2 minutes ago| A|Martin Bernstorff| N||",
            1,
            LogEntry(
                time_since=datetime.timedelta(minutes=2),
                hash="123456",
                author="Martin Bernstorff",
                notes="",
                statuses=Statuses(values=["?"], size=1),
            ),
        ),
    ],
)
def test_log_entry_parsing(input: str, n_statuses: int, expected: LogEntry):
    entry = LogEntry.from_str(input, n_statuses)
    assert entry.__str__() == expected.__str__()


def test_status_setting_from_empty():
    entry = LogEntry(
        time_since=datetime.timedelta(minutes=2),
        hash="123456",
        author="Martin Bernstorff",
        notes="",
        statuses=Statuses(values=[], size=2),
    )

    entry.set_ok(0)
    assert entry.statuses.values == ["G", "?"]
