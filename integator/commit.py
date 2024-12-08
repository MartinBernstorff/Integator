import datetime as dt
import re

import pytimeparse  # type: ignore

from integator.basemodel import BaseModel  # type: ignore


class Commit(BaseModel):
    hash: str
    timestamp: dt.datetime
    author: str

    @staticmethod
    def from_str(line: str) -> "Commit":
        dto = parse_commit_str(line)

        return Commit(
            hash=str(dto.hash),
            timestamp=dto.timestamp,
            author=str(dto.author),
        )

    def age(self) -> dt.timedelta:
        return dt.datetime.now() - self.timestamp


class CommitDTO(BaseModel):
    FORMAT_STR = "C|%h| T|%ar| A|%aN| N|%N%-C()|%-C()"

    hash: str
    timestamp: dt.datetime
    author: str
    notes: str


def parse_commit_str(line: str):
    regexes = [
        ("hash", r"^C\|(.*?)\|"),
        ("timestamp", r"T\|(.*?)\s+ago\|"),
        ("author", r"A\|(.*?)\|"),
        ("notes", r"N\|(.*?)\|"),
    ]

    results = {}

    for name, regex in regexes:
        match = re.search(regex, line)

        if match is None:
            raise ValueError(f"Could not find {name} in {line}")

        result: str = match.group(1)  # type: ignore

        if name == "timestamp":
            seconds = pytimeparse.parse(result)  # type: ignore

            if seconds is None:
                raise ValueError(f"Invalid time: {result}")

            time_since = dt.datetime.now() - dt.timedelta(seconds=seconds)

            results[name] = time_since
        elif name == "notes":
            if result == "":
                results[name] = '{"values": []}'
            else:
                results[name] = result
        else:
            results[name] = result if match else ""

    return CommitDTO(**results)  # type: ignore
