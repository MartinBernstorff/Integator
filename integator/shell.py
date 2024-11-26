import enum
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ExitCode(enum.Enum):
    OK = 0
    ERROR = 1


@dataclass
class RunResult:
    exit_code: ExitCode
    error_message: str | None


class Stream(enum.Enum):
    YES = True
    NO = False


class Shell:
    def clear(self) -> None:
        print("\033c", end="")

    def run(
        self,
        command: str,
        output_file: Path,
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
            with open(output_file, "w") as f:
                process = subprocess.Popen(
                    [command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    shell=True,
                )

                # Stream output
                while True:
                    output = process.stdout.readline()
                    if output == "" and process.poll() is not None:
                        break
                    if output:
                        # Write to file
                        f.write(output)
                        f.flush()

                        # Optionally write to terminal
                        if stream == Stream.YES:
                            sys.stdout.write(output)
                            sys.stdout.flush()

                # Get return code
                return_code = process.poll()
                return RunResult(
                    exit_code=ExitCode.OK if return_code is None else ExitCode.ERROR,
                    error_message=None,
                )
        except Exception as e:
            return RunResult(
                exit_code=ExitCode.ERROR,
                error_message=str(e),
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
