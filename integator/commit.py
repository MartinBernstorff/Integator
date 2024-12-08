import datetime as dt
import re

from integator.basemodel import BaseModel


def parse_commit_str(line: str):
    regexes = [
        ("hash", r"^C\|(.*?)\|"),
        ("timestamp", r"T\|(.*?)\|"),
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
            results[name] = dt.datetime.fromisoformat(result).replace(tzinfo=None)
        elif name == "notes":
            if result == "":
                results[name] = '{"values": []}'
            else:
                results[name] = result
        else:
            results[name] = result if match else ""

    return CommitDTO(**results)  # type: ignore


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
    hash: str
    timestamp: dt.datetime
    author: str
    notes: str
