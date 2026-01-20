import argparse

from agents.orchestrator import run_loop as run_orchestrator
from agents.reporter import run_loop as run_reporter
from agents.validator import run_loop as run_validator


def main() -> None:
    parser = argparse.ArgumentParser(description="Kompline agents runner")
    parser.add_argument(
        "agent",
        choices=["orchestrator", "validator", "reporter"],
        help="Agent role to run",
    )
    args = parser.parse_args()

    if args.agent == "orchestrator":
        run_orchestrator()
    elif args.agent == "validator":
        run_validator()
    elif args.agent == "reporter":
        run_reporter()


if __name__ == "__main__":
    main()
