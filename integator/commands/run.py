import logging
import pathlib

import typer

from integator.commands.argument_parsing import (
    commit_match_or_latest,
    get_settings,
    hash_defaults,
    step_defaults,
    step_match_or_all,
    template_defaults,
)
from integator.git import Git, RootWorktree
from integator.logging import init_log
from integator.run_step import run_step
from integator.shell import ExitCode, RunResult
from integator.step_status_repo import StepStatusRepo

logger = logging.getLogger(__name__)

run_app = typer.Typer()


@run_app.command("r")
@run_app.command()
def run(
    hash: str | None = hash_defaults,
    step: str | None = step_defaults,
    template_name: str | None = template_defaults,
    debug: bool = False,
    quiet: bool = False,
):
    """Runs all steps for the current commit (default), or for a given commit (--hash argument), or for a given step (--step)."""
    init_log(debug, quiet)
    settings = get_settings(template_name)

    git = Git(source_dir=settings.integator.root_worktree_dir)
    commit = commit_match_or_latest(hash, git)
    steps = step_match_or_all(step, settings)

    # Existing statuses are wiped when calling run.
    # Downside is repeat work. Upside is that `run` always runs, which is what we expect.
    # To avoid repeat work, we can run `check` first.
    StepStatusRepo.clear(commit, steps)

    results: list[RunResult] = []
    for step_spec in steps:
        # Also updates the statuses.
        result = run_step(
            step=step_spec,
            commit=commit,
            root_worktree=RootWorktree(git=Git(settings.integator.root_worktree_dir)),
            status_repo=StepStatusRepo(),
            output_dir=pathlib.Path(".logs"),
            quiet=quiet,
        )
        match result.exit:
            # Logs are output during run_step, so no need to print the logs
            case ExitCode.OK:
                logger.info(f"Step {step_spec.name} succeeded")
            case ExitCode.ERROR:
                logger.error(f"Step {step_spec.name} failed")
                if settings.integator.fail_fast:
                    logger.error("Fail fast enabled. Exiting.")
                    break

        results.append(result)

    statuses = StepStatusRepo().get(commit.hash)

    if statuses.all_succeeded({step.name for step in steps}):
        logger.info("All steps succeeded")
    else:  # At least one failed
        logger.error("At least one step failed")
        raise typer.Exit(code=ExitCode.ERROR.value)
