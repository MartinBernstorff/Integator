import re

import pydantic

from integator.shell import Shell
from integator.task_status import Statuses


class TaskStatusRepo:
    FORMAT_STR = '--pretty=format:"C|%h| T|%ar| A|%aN| N|%N%-C()|%-C()"'

    @staticmethod
    def get(hash: str) -> Statuses:
        log_str = Shell().run_quietly(f"git log -1 {hash} {TaskStatusRepo.FORMAT_STR}")

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
        notes = statuses.model_dump_json()
        Shell().run_quietly(f"git notes add -f -m '{notes}' {hash}")
