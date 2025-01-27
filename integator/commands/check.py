import logging

import typer

from integator.commands.argument_parsing import (
    commit_match_or_latest,
    get_settings,
    hash_defaults,
    step_defaults,
    step_match_or_all,
    template_defaults,
)
from integator.git import Git
from integator.sys_logs import init_log
from integator.shell import ExitCode
from integator.step_status_repo import StepStatusRepo

check_app = typer.Typer()

logger = logging.getLogger(__name__)


@check_app.command("c")
@check_app.command()
def check(
    hash: str | None = hash_defaults,
    step: str | None = step_defaults,
    template_name: str | None = template_defaults,
    debug: bool = False,
    quiet: bool = False,
):
    """Checks the combined status of all (default) or one (--step) step, for latest or a given commit (--hash). Does no modification of statuses."""
    init_log(debug, quiet)
    settings = get_settings(template_name)

    commit = commit_match_or_latest(hash, Git(settings.integator.root_worktree_dir))

    logger.info(f"Checking statuses for commit {commit.hash}")

    steps = step_match_or_all(step, settings)
    statuses = StepStatusRepo().get(commit.hash)

    step_names = {step.name for step in steps}
    if statuses.all_succeeded(step_names):
        logger.info(f"{step_names} succeeded")
    else:
        logger.error(f"At least one step failed: {statuses.get_failures()}")
        raise typer.Exit(code=ExitCode.ERROR.value)
