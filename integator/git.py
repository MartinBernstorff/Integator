import functools
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


@functools.cache
def _get_change_count(source_dir: pathlib.Path, hash: str) -> ChangeCount:
    maybeResult = Shell().run_quietly(f"git -C {source_dir} show --shortstat {hash}")
    if not maybeResult:
        raise RuntimeError("No commit found")

    patterns = {
        "files": r"(\d+) fil.+",
        "insertions": r"^.+(\d+) ins.+",
        "deletions": r"^.+(\d+) del.+",
    }

    values: dict[str, int] = {}
    for pattern_name, regex in patterns.items():
        match = re.search(regex, maybeResult[-1])
        if match is None:
            values[pattern_name] = 0
        else:
            values[pattern_name] = int(match.group(1))

    return ChangeCount(
        values["files"],
        values["insertions"],
        values["deletions"],
    )


@dataclass
class Git:
    source_dir: pathlib.Path
    log: GitLog

    def change_count(self, hash: str) -> ChangeCount:
        return _get_change_count(self.source_dir, hash)

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

    def checkout(self, commit: str):
        Shell().run_quietly(f"git checkout {commit}")


@dataclass
class SourceGit:
    # The git representation for the location of the source files. E.g. used for monitoring, finding commits etc.
    git: Git

    def init_worktree(self, path: pathlib.Path, hash: str):
        if path.exists():
            print("Worktree already exists, continuing")
        else:
            Shell().run_quietly(f"git worktree add -d '{path}' {hash}")
        return path
