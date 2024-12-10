import pathlib
import re
from dataclasses import dataclass

from integator.git_log import GitLog
from integator.shell import Shell


@dataclass
class ChangeCount:
    files: int
    insertions: int
    deletions: int


@dataclass
class Git:
    source_dir: pathlib.Path
    log: GitLog

    def change_count(self, hash: str) -> ChangeCount:
        maybeResult = Shell().run_quietly(
            f"git -C {self.source_dir} show --shortstat {hash}"
        )
        if not maybeResult:
            raise RuntimeError("No commit found")

        changes = maybeResult[-1]
        regex = r"(\d+).+(\d+).+(\d+)"
        matches = re.search(regex, changes)
        if not matches:
            raise RuntimeError("Could not parse changes")
        return ChangeCount(
            int(matches.group(1)),
            int(matches.group(2)),
            int(matches.group(3)),
        )

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
