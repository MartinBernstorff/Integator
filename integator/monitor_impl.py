import datetime
import time

from integator.config import Command
from integator.git import Git
from integator.log_entry import LogEntry
from integator.shell import Shell


def monitor_impl(commands: list[tuple[int, Command]], shell: Shell, n_statuses: int):
    # Create the worktree and switch to it

    while True:
        entries = Git().get_log(n_statuses=n_statuses)
        latest_entry = entries[-1]

        for position, cmd in commands:
            if _is_stale(entries, cmd, position):
                print(f"Running {cmd.name}")
                try:
                    shell.run(cmd.cmd)
                    latest_entry.set_ok(position)
                except Exception as e:
                    latest_entry.set_failed(position)

                Git().update_notes(latest_entry.note())

        time.sleep(1)


def _is_stale(entries: list[LogEntry], cmd: Command, position: int) -> bool:
    successes = [entry for entry in entries if entry.is_ok(position)]

    time_since_success = (
        successes[0].time_since if successes else datetime.timedelta(days=30)
    )

    return time_since_success > datetime.timedelta(seconds=cmd.max_staleness_seconds)
