import pathlib
from dataclasses import dataclass

from integator.commit import Commit
from integator.shell import Shell


@dataclass
class Log:
    def get(self) -> list[Commit]:
        values = Shell().run_quietly(
            'git log -n 10 --pretty=format:"C|%h| T|%ar| A|%aN| N|%N%-C()|%-C()"'
        )

        if not values:
            raise RuntimeError("No values returned from git log")

        entries = [Commit.from_str(value) for value in values]
        return entries

    def latest(self) -> Commit:
        return self.get()[0]


@dataclass
class Git:
    source_dir: pathlib.Path
    log: Log

    def diff_against(self, reference: str) -> list[str]:
        result = Shell().run_quietly(f"git diff origin/{reference}")
        if not result:
            return []
        return result

    def push_head(self):
        latest_commit = self._latest_commit()
        source_branch = self._source_branch()

        Shell().run_quietly(f"git push origin {latest_commit}:{source_branch}")

    def _latest_commit(self) -> str:
        values = Shell().run_quietly(f"git -C {self.source_dir} rev-parse HEAD")
        if not values:
            raise RuntimeError("No commit found")
        return values[0]

    def _source_branch(self) -> str:
        values = Shell().run_quietly(f"git -C {self.source_dir} branch --show-current")

        if not values:
            raise RuntimeError("No branch found")

        return values[0]

    def checkout_head(self):
        latest_commit = self._latest_commit()
        Shell().run_quietly(f"git checkout {latest_commit}")
