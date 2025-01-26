import logging
import pathlib
import time
from functools import partial
from multiprocessing import Process

import typer

from integator.commit import Commit
from integator.git import Git, RootWorktree
from integator.log import log_impl
from integator.run_step import run_step
from integator.settings import FILE_NAME, RootSettings, StepSpec, find_settings_file
from integator.shell import ExitCode, RunResult, Shell
from integator.step_status_repo import StepStatusRepo
from integator.watch_impl import CommandRan, watch_impl

logger = logging.getLogger(__name__)
format = "%(asctime)s \t%(levelname)s \t%(name)s \t%(message)s"
date_fmt = "%H:%M:%S"


def init_log(debug: bool, quiet: bool):
    log_level = logging.ERROR if quiet else logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format=format,
        datefmt=date_fmt,
    )


app = typer.Typer()

# refactor: It might make sense to convert these commands to their own files, as
# they seem to be growing. But I'm not sure how to do that with Typer.
# Just importing the app object causes circular imports. Similar problem with routes in
# This would also remove the watch/watch_impl separation, which duplicates a lot of logic.


@app.command("r")
@app.command()
def run(
    hash: str | None = typer.Option(None, "--hash", help="Commit hash to check"),
    step: str | None = typer.Option(None, "--step", help="Step to check"),
    debug: bool = False,
    quiet: bool = False,
):
    # Runs all steps for the current commit (default), or for a given commit (--hash argument), or for a given step (--step).
    init_log(debug, quiet)
    settings = RootSettings()
    git = Git(source_dir=settings.integator.source_dir)
    commit = commit_match_or_latest(hash, git)

    # Existing statuses are wiped when calling run.
    # Downside is repeat work. Upside is that `run` always runs, which is what we expect.
    # To avoid repeat work, we can run `check` first.
    StepStatusRepo.clear(commit)

    results: list[RunResult] = []
    for step_spec in step_match_or_all(step, settings):
        # Also updates the statuses.
        result = run_step(
            step=step_spec,
            commit=commit,
            root_worktree=RootWorktree(git=Git(settings.integator.source_dir)),
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

    # XXX: Handle if only one step is specified. Do I even need to check here? Yes, after fail_fast
    if statuses.all_succeeded(set(settings.step_names())):
        logger.info("All steps succeeded")
    else:  # At least one failed
        logger.error("At least one step failed")
        raise typer.Exit(code=ExitCode.ERROR.value)


def commit_match_or_latest(hash: str | None, git: Git) -> Commit:
    match hash:
        case str():
            commit = git.log.get_by_hash(hash)
        case None:
            commit = git.log.latest()
    return commit


def step_match_or_all(step: str | None, settings: RootSettings) -> list[StepSpec]:
    match step:
        case None:
            step_specs = settings.integator.steps
        case str():
            step_specs = [settings.get_step(step)]
    return step_specs


# feat: A `check` command, which checks the combined status of all (default) or one (--step), for latest or a given commit (--hash)
# Does no modification of statuses.
@app.command("c")
@app.command()
def check(
    hash: str | None = typer.Option(None, "--hash", help="Commit hash to check"),
    step: str | None = typer.Option(None, "--step", help="Step to check"),
    debug: bool = False,
    quiet: bool = False,
):
    init_log(debug, quiet)
    settings = RootSettings()  # type: ignore # noqa: F841

    commit = commit_match_or_latest(hash, Git(settings.integator.source_dir))

    logger.info(f"Checking statuses for commit {commit.hash}")

    steps = step_match_or_all(step, settings)
    statuses = StepStatusRepo().get(commit.hash)

    if statuses.all_succeeded({step.name for step in steps}):
        logger.info("All steps succeeded")
    else:
        logger.error(f"At least one step failed: {statuses.get_failures()}")
        raise typer.Exit(code=ExitCode.ERROR.value)


#
# feat: A `clear` command, which removes all step states for a given commit. By default, removes for the latest commit.

# ?: We do not want to use an existing DAG tool as the job-engine, because that makes it very hard to get step status,
# and therefore how to present it nicely and log it to persistence.


@app.command("i")
@app.command()
def init():
    settings = RootSettings()

    # feat: add a selector here, to choose from existing files in ~/.config/integator/templates
    # Then we can have e.g. a Python.toml template, which can be used as a starting point.
    # Perhaps we want merging of the default with whichever settings are specified in the template?
    # This means we can
    destination_dir = find_settings_file()
    match destination_dir:
        case pathlib.Path():
            print(f"Settings file already exists at: {destination_dir}")
        case None:
            new_path = pathlib.Path.cwd() / FILE_NAME
            settings.write_toml(new_path)
            print(f"Settings file created at: {new_path}")

    gitignore_path = pathlib.Path.cwd() / ".gitignore"
    match gitignore_path.exists():
        case True:
            update_gitignore(gitignore_path)
        case False:
            pass


def update_gitignore(gitignore_path: pathlib.Path):
    if ".logs/" not in gitignore_path.read_text().strip():
        with open(gitignore_path, "a") as f:
            f.write("\n.logs/")
            print("Added .logs to .gitignore")


@app.command("w")
@app.command()
def watch(debug: bool = False, quiet: bool = False):
    init_log(debug, quiet)

    settings = RootSettings()

    shell = Shell()
    while True:
        logger.debug("--- Init'ing ---")
        git = Git(source_dir=settings.integator.source_dir)

        logger.debug("Running")
        logger.info(
            f"Integator {settings.version()}: Watching {settings.integator.source_dir} for new commits"
        )
        status = watch_impl(
            shell,
            root_git=git,
            status_repo=StepStatusRepo(),
            quiet=quiet,
        )

        logger.debug("--- Sleeping ---")
        if status == CommandRan.NO:
            time.sleep(1)


@app.command("t")
@app.command()
def tui(debug: bool = False, quiet: bool = True):
    init_log(debug, quiet)
    from integator.tui.main import IntegatorTUI

    side_process = Process(target=partial(watch, debug, quiet=quiet), daemon=True)
    side_process.start()

    app = IntegatorTUI()
    app.run()


@app.command("l")
@app.command()
def log(debug: bool = False, quiet: bool = False):
    init_log(debug, quiet)
    log_impl(debug)


if __name__ == "__main__":
    app()
