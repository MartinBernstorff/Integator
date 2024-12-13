import datetime as dt

from integator.commit import parse_commit_str


def test_parse_commit_str():
    val = "C|aa85f0e| T|2024-12-08T18:07:04+01:00| A|Martin Bernstorff| N||"
    parsed = parse_commit_str(val)
    assert parsed.hash == "aa85f0e"
    assert parsed.timestamp == dt.datetime(2024, 12, 8, 18, 7, 4)
    assert parsed.author == "Martin Bernstorff"
    assert parsed.notes == '{"values": []}'
