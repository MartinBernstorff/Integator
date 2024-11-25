import datetime

from git import LogEntry


def test_parse_from_line():
    line = "af7b573 2 minutes ago Martin Bernstorff ✅"
    entry = LogEntry.parse_from_line(line)

    assert entry.hash == "af7b573"
    assert entry.time_since == datetime.timedelta(minutes=2)
    assert entry.rest == "Martin Bernstorff ✅"


def test_parse_from_line_hours():
    line = "af7b573 2 hours ago Martin Bernstorff ✅"
    entry = LogEntry.parse_from_line(line)

    assert entry.hash == "af7b573"
    assert entry.time_since == datetime.timedelta(hours=2)
    assert entry.rest == "Martin Bernstorff ✅"
