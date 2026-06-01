from __future__ import annotations

from pathlib import Path

import pytest

from mechaudit.case_loader import CaseLoadError, load_benchmark_cases, load_case_file, split_cases
from mechaudit.pressure_vessel import audit_case
from mechaudit.report_writer import write_markdown_report


ROOT = Path(__file__).resolve().parents[1]


def test_pending_real_world_cases_skip_without_count_assumption() -> None:
    cases = load_benchmark_cases(ROOT)
    _, skipped = split_cases(cases)
    real_pending = [case for case in skipped if case.source_type == "real_world"]

    assert real_pending
    for case in real_pending:
        result = audit_case(case)
        assert result.skipped
        assert result.skip_reason == "pending_capture"


def test_completed_real_world_cases_load_and_can_report(tmp_path: Path) -> None:
    cases = load_benchmark_cases(ROOT)
    complete, _ = split_cases(cases)
    complete_real = [case for case in complete if case.source_type == "real_world"]

    for case in complete_real:
        result = audit_case(case)
        report_path = write_markdown_report(result, tmp_path)
        assert report_path.exists()
        assert report_path.read_text(encoding="utf-8").startswith("# Audit Report:")


def test_malformed_benchmark_metadata_reports_p01(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.md"
    malformed.write_text("```json\n{\"case_id\": \"bad\"\n```\n", encoding="utf-8")

    with pytest.raises(CaseLoadError) as exc_info:
        load_case_file(malformed)

    assert exc_info.value.failure_mode == "P-01"
