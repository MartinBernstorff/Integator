from dataclasses import dataclass

from integator.commit import Commit
from integator.shell import Shell


@dataclass
class GitLog:
    def get(self) -> list[Commit]:
        values = Shell().run_quietly(f'git log -n 10 --pretty=format:"{FORMAT_STR}"')

        if not values:
            raise RuntimeError("No values returned from git log")

        entries = [Commit.from_str(value) for value in values]
        return entries

    def latest(self) -> Commit:
        return self.get()[0]


FORMAT_STR = "C|%h| T|%aI| A|%aN| N|%N%-C()|%-C()"
