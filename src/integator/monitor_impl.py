import time

from src.integator.config import Command
from src.integator.git import Git


def monitor_impl(commands: list[Command]):
    while True:
        # Check if the commands are stale
        # If so, run the commands
        Git.impl().log()
        time.sleep(1)