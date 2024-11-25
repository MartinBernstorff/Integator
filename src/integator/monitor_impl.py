import datetime
import time

from integator.config import Command
from integator.git import Git, LogEntry
from integator.shell import Shell


def monitor_impl(commands: list[Command]):
    # Create the worktree and switch to it

    while True:
        # Check if the commands are stale. If so, run them.
        Git.impl().log()
        time.sleep(1)

def _is_stale(entries: list[LogEntry], cmd: Command, cmd_position: int) -> bool:
    successes = [entry for entry in entries if entry.is_ok(cmd_position)]
    if not successes:
        return True

    return successes[-1].time_since > datetime.timedelta(seconds=cmd.max_staleness_seconds)


def _run_cmd(cmd: Command):
    # Run the command in the correct directory
    print(f"Running command: {cmd.cmd}")
    Shell.impl().run(cmd.cmd)

    # Update the emoji position
