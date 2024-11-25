import datetime

from integator.log_entry import LogEntry


def test_parse_from_line():
    line = "af7b573 2 minutes ago Martin Bernstorff [✅😁]"
    entry = LogEntry.from_str(line, 2)

    assert entry.hash == "af7b573"
    assert entry.time_since == datetime.timedelta(minutes=2)
    assert entry.notes == ""
    assert entry.statuses == ["✅", "😁"]


def test_parse_from_line_hours():
    line = "af7b573 2 hours ago Martin Bernstorff [✅]"
    entry = LogEntry.from_str(line, 1)

    assert entry.hash == "af7b573"
    assert entry.time_since == datetime.timedelta(hours=2)
    assert entry.author == "Martin Bernstorff"
    assert entry.notes == ""
    assert entry.statuses == ["✅"]
