import logging
import time

import typer

from integator.commands.argument_parsing import get_settings, template_defaults
from integator.git import Git
from integator.sys_logs import init_log
from integator.shell import Shell
from integator.step_status_repo import StepStatusRepo
from integator.watch_impl import CommandRan, watch_impl

watch_app = typer.Typer()


logger = logging.getLogger(__name__)


# refactor: This would also remove the watch/watch_impl separation, which adds needless indirection.
@watch_app.command("w")
@watch_app.command()
def watch(
    template_name: str | None = template_defaults,
    debug: bool = False,
    quiet: bool = False,
):
    # feat: Do I want to remove the watch command completely? Or how does this work? What role does it still play?
    # If I want to keep it, do I want it to be able to watch only a specific step?
    init_log(debug, quiet)
    settings = get_settings(template_name)

    shell = Shell()
    while True:
        logger.debug("--- Init'ing ---")
        git = Git(source_dir=settings.integator.root_worktree_dir)

        logger.debug("Running")
        logger.info(
            f"Integator {settings.version()}: Watching {settings.integator.root_worktree_dir} for new commits"
        )
        status = watch_impl(
            shell,
            root_git=git,
            status_repo=StepStatusRepo(),
            quiet=quiet,
            settings=settings,
        )

        logger.debug("--- Sleeping ---")
        if status == CommandRan.NO:
            time.sleep(1)
