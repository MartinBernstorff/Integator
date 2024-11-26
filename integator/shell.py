import enum
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ExitCode(enum.Enum):
    OK = 0
    ERROR = 1

    @staticmethod
    def from_int(value: int | None) -> "ExitCode":
        if value is None:
            return ExitCode.ERROR
        if value == 0:
            return ExitCode.OK
        return ExitCode.ERROR


@dataclass
class RunResult:
    exit_code: ExitCode
    output: str | None


class Stream(enum.Enum):
    YES = True
    NO = False


class Shell:
    def clear(self) -> None:
        print("\033c", end="")

    def _append_text(self, text: str, file: Path) -> None:
        with file.open("a") as f:
            f.write(text)

    def run(
        self,
        command: str,
        output_file: Path | None = None,
        stream: Stream = Stream.YES,
    ) -> RunResult:
        """
        Runs a shell script and streams the output to a file, optionally displaying in terminal.

        Args:
            script_path: Path to the shell script to execute
            output_file: Path where the output should be saved
            stream_to_terminal: If True, also display output in terminal
            shell: If True, run command through shell

        Returns:
            Tuple containing (return_code, error_message)
        """
        try:
            process = subprocess.Popen(
                [command],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                shell=True,
            )
            lines = []

            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break

                if output:
                    lines.append(output)

                    # Optionally write to terminal
                    if stream == Stream.YES:
                        sys.stdout.write(output)
                        sys.stdout.flush()

                    if output_file:
                        self._append_text(output, output_file)

            # Get return code
            return_code = ExitCode.from_int(process.poll())

            if output_file:
                self._append_text(f"{return_code}", output_file)

            return RunResult(
                exit_code=return_code,
                output="".join(lines),
            )
        except Exception as e:
            return RunResult(
                exit_code=ExitCode.ERROR,
                output=str(e),
            )

    def run_interactively(self, command: str) -> None:
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

    def run_quietly(self, command: str) -> Optional[list[str]]:
        try:
            return (
                subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                .decode("utf-8")
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"""{command} failed.
    Exit code: {e.returncode}
    Output: {e.stdout.decode('utf-8').strip()}"""
            ) from e
