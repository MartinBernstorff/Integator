from integator.commit import Hash
from integator.shell import Shell
from integator.task_status import Statuses


class TaskStatusRepo:
    FORMAT_STR = '--pretty=format:"C|%h| T|%ar| A|%aN| N|%N%-C()|%-C()"'

    @staticmethod
    def get(hash: Hash) -> Statuses:
        log_str = Shell().run_quietly(f"git log -1 {hash} {TaskStatusRepo.FORMAT_STR}")

        if not log_str:
            raise RuntimeError("No values returned from git log")

        if len(log_str) > 1:
            raise RuntimeError("More than one commit matches hash")

        return Statuses.from_str(log_str[0])

    @staticmethod
    def update(hash: Hash, statuses: Statuses):
        notes = statuses.model_dump_json()
        Shell().run_quietly(f"git notes add -f -m '{notes}' {hash}")
