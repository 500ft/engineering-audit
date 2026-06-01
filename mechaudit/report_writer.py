from __future__ import annotations

from pathlib import Path

from .audit_result import AuditResult


def write_markdown_report(result: AuditResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{result.case_id}.md"

    lines = [
        f"# Audit Report: {result.case_id}",
        "",
        f"- Source: `{result.source_path}`",
        f"- Status: `{result.status}`",
        f"- Skipped: `{str(result.skipped).lower()}`",
    ]
    if result.skip_reason:
        lines.append(f"- Skip reason: `{result.skip_reason}`")
    lines.extend(
        [
            f"- Expected failure modes: {', '.join(result.expected_failure_modes) or 'none'}",
            f"- Detected failure modes: {', '.join(result.detected_failure_modes) or 'none'}",
            f"- Result: {'PASS' if result.passed else 'FAIL'}",
            "",
            "## Recomputed Values",
            "",
        ]
    )

    if result.recomputed_values:
        for key, value in sorted(result.recomputed_values.items()):
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Checks", ""])
    for check in result.checks:
        marker = "PASS" if check.passed else "FAIL"
        mode = f" ({check.detected_failure_mode})" if check.detected_failure_mode else ""
        lines.append(f"- `{marker}` `{check.name}`{mode}: {check.message}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
