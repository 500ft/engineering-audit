"""Command-line entry point for MechAudit.

Two subcommands:

- ``mechaudit audit <case_file> [-o OUT]`` — audit a benchmark case file and
  write a Markdown report (the original behavior).
- ``mechaudit capture ...`` — record a verbatim model output as an immutable,
  hash-verified provenance artifact. This never calls a model or the network;
  the raw output is supplied via ``--output-file`` or stdin.

For backward compatibility, if the first argument is not a known subcommand the
invocation is treated as ``audit`` (so ``mechaudit path/to/case.md`` still works).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .capture import CaptureError, capture_run
from .case_loader import CaseLoadError, load_case_file
from .pressure_vessel import audit_case
from .report_writer import write_markdown_report


SUBCOMMANDS = {"audit", "capture"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mechaudit",
        description="Audit LLM-generated engineering calculations and capture model outputs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser(
        "audit",
        help="Audit a benchmark case file and write a markdown report.",
    )
    audit.add_argument(
        "case_file",
        type=Path,
        help="Path to a benchmark case markdown file (with a fenced JSON metadata block).",
    )
    audit.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to write the markdown report to. Defaults to reports/<case_id>.md.",
    )

    capture = subparsers.add_parser(
        "capture",
        help=(
            "Record a verbatim model output as an immutable, hash-verified "
            "artifact. Does NOT call any model or network; supply the raw output "
            "via --output-file or stdin."
        ),
    )
    capture.add_argument("--prompt-id", required=True, help="Stable prompt identifier.")
    prompt_source = capture.add_mutually_exclusive_group(required=True)
    prompt_source.add_argument(
        "--prompt-file", type=Path, help="File containing the verbatim prompt text."
    )
    prompt_source.add_argument(
        "--prompt-text", type=str, help="Verbatim prompt text (inline)."
    )
    capture.add_argument("--model", required=True, help="Model product name, e.g. gpt-5.")
    capture.add_argument("--model-version", default=None, help="Model version/release id.")
    capture.add_argument("--provider", default=None, help="Provider/vendor, e.g. openai.")
    capture.add_argument(
        "--run-date", required=True, help="ISO date of the model run (YYYY-MM-DD)."
    )
    capture.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="File holding the verbatim raw model output. Reads stdin if omitted.",
    )
    capture.add_argument(
        "--tier",
        choices=["gold", "silver"],
        default="gold",
        help="Provenance tier. gold = verbatim API response; silver = verbatim UI transcript.",
    )
    capture.add_argument(
        "--protocol",
        choices=["standard", "challenge", "organic"],
        default="standard",
        help="Capture protocol.",
    )
    capture.add_argument(
        "--metadata-source",
        choices=["api", "self_report"],
        default="api",
        help="How model/version/date were obtained.",
    )
    capture.add_argument(
        "--kind",
        choices=["raw_response", "api_response"],
        default="raw_response",
        help="Artifact kind for the stored output.",
    )
    capture.add_argument("--temperature", type=float, default=None)
    capture.add_argument("--reasoning-effort", default=None)
    capture.add_argument("--notes", default="", help="Free-text capture notes.")
    capture.add_argument(
        "--captures-root",
        type=Path,
        default=Path("."),
        help="Repository root under which the captures/ tree lives. Defaults to cwd.",
    )
    capture.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing output bytes for this run id if they differ.",
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


def _run_audit(args: argparse.Namespace) -> int:
    try:
        report_path = run(args.case_file, args.output)
    except CaseLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote report to {report_path}")
    return 0


def _run_capture(args: argparse.Namespace) -> int:
    if args.prompt_file is not None:
        prompt_text = args.prompt_file.read_text(encoding="utf-8")
    else:
        prompt_text = args.prompt_text

    if args.output_file is not None:
        raw_output = args.output_file.read_bytes()
    else:
        raw_output = sys.stdin.buffer.read()

    try:
        result = capture_run(
            args.captures_root,
            prompt_id=args.prompt_id,
            prompt_text=prompt_text,
            model_name=args.model,
            raw_output=raw_output,
            run_date=args.run_date,
            provider=args.provider,
            model_version=args.model_version,
            provenance_tier=args.tier,
            capture_protocol=args.protocol,
            metadata_source=args.metadata_source,
            output_kind=args.kind,
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
            notes=args.notes,
            overwrite=args.overwrite,
        )
    except CaptureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Captured run {result.run_id}")
    print(f"  record:  {result.record_path}")
    for artifact in result.record.artifacts:
        print(f"  {artifact.kind}: {artifact.path} ({artifact.sha256})")
    return 0


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    # Backward compatibility: bare `mechaudit <case_file>` still means audit.
    if raw_args and raw_args[0] not in SUBCOMMANDS and not raw_args[0].startswith("-"):
        raw_args = ["audit", *raw_args]

    parser = build_parser()
    args = parser.parse_args(raw_args)

    if args.command == "capture":
        return _run_capture(args)
    return _run_audit(args)


if __name__ == "__main__":
    sys.exit(main())
