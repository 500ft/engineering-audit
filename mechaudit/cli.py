"""Command-line entry point for running MechAudit against a single case file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .case_loader import CaseLoadError, load_case_file
from .pressure_vessel import audit_case
from .report_writer import write_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mechaudit",
        description="Audit a benchmark case file and write a markdown report.",
    )
    parser.add_argument(
        "case_file",
        type=Path,
        help="Path to a benchmark case markdown file (with a fenced JSON metadata block).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Path to write the markdown report to. "
            "Defaults to reports/<case_id>.md."
        ),
    )
    return parser


def run(case_file: Path, output: Path | None) -> Path:
    case = load_case_file(case_file)
    result = audit_case(case)

    if output is None:
        output_dir = Path("reports")
        return write_markdown_report(result, output_dir)

    report_path = write_markdown_report(result, output.parent)
    default_path = output.parent / f"{result.case_id}.md"
    if default_path != output:
        default_path.replace(output)
        return output
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report_path = run(args.case_file, args.output)
    except CaseLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
