import logging
import re

import pydantic

from integator.commit import Commit
from integator.shell import Shell
from integator.step_status import Statuses

log = logging.getLogger(__name__)


class StepStatusRepo:
    FORMAT_STR = '--pretty=format:"C|%h| T|%ar| A|%aN| N|%N%-C()|%-C()"'

    @staticmethod
    def clear(commit: Commit):
        log.debug(f"Clearing notes for {commit.hash}")
        try:
            Shell().run_quietly(f"git notes remove {commit.hash}")
        except RuntimeError as e:
            # If no note exists, we don't need to error
            if "has not note" not in str(e):
                pass
            else:
                raise e

    @staticmethod
    def get(hash: str) -> Statuses:
        log.debug(f"Getting notes for {hash}")
        log_str = Shell().run_quietly(f"git log -1 {hash} {StepStatusRepo.FORMAT_STR}")

        if len(log_str) > 1:
            raise RuntimeError("More than one commit matches hash")

        notes = re.search(r"N\|(.*?)\|", log_str[0])

        if not notes:
            raise RuntimeError("No values returned from git log")

        try:
            return Statuses.from_str(notes.groups()[0])
        except pydantic.ValidationError:
            return Statuses()

    @staticmethod
    def update(hash: str, statuses: Statuses):
        log.debug(f"Updating notes for {hash} with {statuses.names()}")
        notes = statuses.model_dump_json()
        Shell().run_quietly(f"git notes add -f -m '{notes}' {hash}")
