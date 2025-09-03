import logging
import re

import pydantic

from integator.commit import Commit
from integator.settings import StepSpec
from integator.shell import Shell
from integator.step_status import Statuses

log = logging.getLogger(__name__)


class StepStatusRepo:
    FORMAT_STR = '--pretty=format:"C|%h| T|%ar| A|%aN| N|%N%-C()|%-C()"'

    @staticmethod
    def clear(commit: Commit, steps: list[StepSpec]):
        log.debug(f"Clearing notes for {commit.hash}")

        statuses = StepStatusRepo.get(commit.hash)

        for step in steps:
            statuses.remove(step.name)

        # Persist the cleared statuses back to git notes
        StepStatusRepo.update(commit.hash, statuses)

    # refactor: instead of a hash, should we take a commit, to be even more type-safe?
    # OTOH, it is less flexible, and sets an artificially high requirement set.
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
