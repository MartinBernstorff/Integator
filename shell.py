import subprocess
from abc import ABC
from typing import Optional


class Shell(ABC):
    def interactive_cmd(self, command: str) -> None: ...

    def run(self, command: str) -> Optional[str]: ...

    @staticmethod
    def impl() -> "Shell":
        return ShellImpl()


class ShellImpl(Shell):
    def interactive_cmd(self, command: str) -> None:
        try:
            subprocess.run(command, shell=True, stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError as e:
            if not e.stdout:
                return

            error_message = f"""{command} failed.
\tExit code: {e.returncode}"""

            if e.stdout:
                error_message += f"\n\tOutput: {e.stdout.decode('utf-8').strip()}"

        raise RuntimeError(error_message) from e

    def run(self, command: str) -> Optional[str]:
        try:
            return (
                subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"""{command} failed.
    Exit code: {e.returncode}
    Output: {e.stdout.decode('utf-8').strip()}"""
            ) from e
