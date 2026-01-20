"""CLI commands for running workers."""

import logging
import threading

import click
from supabase import create_client

from kompline.persistence.scan_store import ScanStore
from kompline.workers.config import SUPABASE_URL, SUPABASE_KEY
from kompline.workers.orchestrator import OrchestratorWorker
from kompline.workers.validator import ValidatorWorker
from kompline.workers.reporter import ReporterWorker


def _get_store() -> ScanStore:
    """Create a ScanStore instance from Supabase config."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise click.ClickException(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return ScanStore(client)


@click.group()
def workers():
    """Run worker processes for distributed compliance auditing."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )


@workers.command()
def orchestrator():
    """Run the orchestrator worker.

    The orchestrator monitors QUEUED scans and creates scan_results
    for validators to process.
    """
    store = _get_store()
    worker = OrchestratorWorker(store)
    worker.run_loop()


@workers.command()
def validator():
    """Run the validator worker.

    The validator processes pending scan results and validates
    compliance items against repositories.
    """
    store = _get_store()
    worker = ValidatorWorker(store)
    worker.run_loop()


@workers.command()
def reporter():
    """Run the reporter worker.

    The reporter monitors completed scans and generates
    compliance reports in Markdown and Korean regulatory formats.
    """
    store = _get_store()
    worker = ReporterWorker(store)
    worker.run_loop()


@workers.command("all")
@click.option(
    "--orchestrator/--no-orchestrator",
    default=True,
    help="Run orchestrator worker"
)
@click.option(
    "--validators",
    default=1,
    type=int,
    help="Number of validator workers to run"
)
@click.option(
    "--reporter/--no-reporter",
    default=True,
    help="Run reporter worker"
)
def all_workers(orchestrator: bool, validators: int, reporter: bool):
    """Run all workers in separate threads.

    By default, runs one orchestrator, one validator, and one reporter.
    Use options to customize which workers to run and how many validators.
    """
    store = _get_store()
    threads: list[threading.Thread] = []

    if orchestrator:
        t = threading.Thread(
            target=OrchestratorWorker(store).run_loop,
            daemon=True,
            name="orchestrator"
        )
        t.start()
        threads.append(t)
        click.echo("Started orchestrator worker")

    for i in range(validators):
        t = threading.Thread(
            target=ValidatorWorker(store).run_loop,
            daemon=True,
            name=f"validator-{i+1}"
        )
        t.start()
        threads.append(t)
        click.echo(f"Started validator worker {i+1}")

    if reporter:
        t = threading.Thread(
            target=ReporterWorker(store).run_loop,
            daemon=True,
            name="reporter"
        )
        t.start()
        threads.append(t)
        click.echo("Started reporter worker")

    click.echo(f"Running {len(threads)} workers. Press Ctrl+C to stop.")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        click.echo("\nShutting down workers...")


if __name__ == "__main__":
    workers()
