import argparse
from pathlib import Path

from .demo import run_demo


def main():
    parser = argparse.ArgumentParser(description="Industrial pump investigation")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run the reproducible synthetic experiment")
    demo.add_argument("--output", type=Path, default=Path("artifacts/demo"))
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--engine", choices=("local", "langgraph"), default="local")
    args = parser.parse_args()
    try:
        report = run_demo(args.output, args.seed, args.engine)
    except ImportError as error:
        parser.exit(2, f"Missing optional dependency: {error}. Install factory-investigator[agents].\n")
    print(report["hypothesis"])
    print(f"Report: {args.output / 'report.md'}")


if __name__ == "__main__":
    main()
