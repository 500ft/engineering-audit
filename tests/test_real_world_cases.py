from __future__ import annotations

from pathlib import Path

import pytest

from mechaudit.case_loader import CaseLoadError, load_benchmark_cases, load_case_file, split_cases
from mechaudit.pressure_vessel import audit_case
from mechaudit.report_writer import write_markdown_report


ROOT = Path(__file__).resolve().parents[1]
# The completed Claude/Gemini fixtures are reviewer-synthesized controls, not
# verbatim captures, so under schema 0.3.0 they are source_type
# "reference_correct" (provenance_tier "deprecated"), no longer "real_world".
REFERENCE_CONTROL_CASE_IDS = {
    "rw-pressure-vessel-gemini-0001",
    "rw-pressure-vessel-claude-0001",
    "rw-pressure-vessel-claude-0002",
}
PENDING_REAL_CASE_IDS = {
    "rw-pressure-vessel-gpt-0001",
    "rw-pressure-vessel-gpt-0002",
}


def test_pending_real_world_cases_skip_without_count_assumption() -> None:
    cases = load_benchmark_cases(ROOT)
    _, skipped = split_cases(cases)
    real_pending = [case for case in skipped if case.source_type == "real_world"]

    assert {case.case_id for case in real_pending} == PENDING_REAL_CASE_IDS
    for case in real_pending:
        result = audit_case(case)
        assert result.skipped
        assert result.skip_reason == "pending_capture"


def test_reference_control_cases_are_no_failure_controls() -> None:
    cases = load_benchmark_cases(ROOT)
    complete, _ = split_cases(cases)
    controls = [case for case in complete if case.source_type == "reference_correct"]

    assert {case.case_id for case in controls} == REFERENCE_CONTROL_CASE_IDS
    for case in controls:
        assert case.source.provenance_tier == "deprecated"
        result = audit_case(case)
        assert not result.skipped
        assert result.expected_failure_modes == []
        assert result.detected_failure_modes == []
        assert result.passed


def test_completed_real_world_cases_preserve_output_conventions() -> None:
    cases = load_benchmark_cases(ROOT)
    claude_plain = next(case for case in cases if case.case_id == "rw-pressure-vessel-claude-0001")

    hoop_outputs = [
        output
        for output in claude_plain.outputs
        if output.source == "llm" and output.name.startswith("hoop_stress")
    ]

    assert {output.convention for output in hoop_outputs} == {"inner_radius", "mean_radius"}
    assert claude_plain.tolerance.accepted_conventions == ["inner_radius", "mean_radius"]


def test_fm10_is_not_emitted_for_real_world_controls() -> None:
    cases = load_benchmark_cases(ROOT)
    complete, _ = split_cases(cases)

    detected_modes = {
        mode
        for case in complete
        for mode in audit_case(case).detected_failure_modes
    }

    assert "FM-10" not in detected_modes


def test_reference_control_cases_load_and_can_report(tmp_path: Path) -> None:
    cases = load_benchmark_cases(ROOT)
    complete, _ = split_cases(cases)
    controls = [case for case in complete if case.source_type == "reference_correct"]

    for case in controls:
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
