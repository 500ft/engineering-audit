from __future__ import annotations

from pathlib import Path

from mechaudit.case_loader import load_benchmark_cases, split_cases
from mechaudit.pressure_vessel import audit_case
from mechaudit.report_writer import write_markdown_report


ROOT = Path(__file__).resolve().parents[1]

# Synthetic single-mode failure cases.
SYNTHETIC_FAILURE_MODES = {
    "syn-fm01-0001": ["FM-01"],
    "syn-fm02a-0001": ["FM-02A"],
    "syn-fm02b-0001": ["FM-02B"],
    "syn-arith-0001": ["FM-03"],
    "syn-fm07-0001": ["FM-07"],
}
# Synthetic analytically/FEA-grade-validated GROUND-TRUTH controls (no failure).
SYNTHETIC_GROUND_TRUTH_CONTROLS = {
    "syn-kt-hole-0001",
    "syn-cantilever-0001",
}


def test_loads_synthetic_cases_and_skips_pending_real_cases() -> None:
    cases = load_benchmark_cases(ROOT)
    complete, skipped = split_cases(cases)

    synthetic = [case for case in complete if case.source_type == "synthetic"]
    synthetic_ids = {case.case_id for case in synthetic}

    expected_ids = set(SYNTHETIC_FAILURE_MODES) | SYNTHETIC_GROUND_TRUTH_CONTROLS
    assert synthetic_ids == expected_ids
    assert len(synthetic) == len(expected_ids)
    assert {case.status for case in skipped} == {"pending_capture"}


def test_synthetic_cases_detect_expected_failure_modes() -> None:
    cases = load_benchmark_cases(ROOT)
    complete, _ = split_cases(cases)
    by_id = {
        case.case_id: case for case in complete if case.source_type == "synthetic"
    }

    for case_id, modes in SYNTHETIC_FAILURE_MODES.items():
        result = audit_case(by_id[case_id])
        assert result.detected_failure_modes == modes
        assert result.passed


def test_synthetic_ground_truth_controls_are_clean() -> None:
    cases = load_benchmark_cases(ROOT)
    complete, _ = split_cases(cases)
    by_id = {
        case.case_id: case for case in complete if case.source_type == "synthetic"
    }

    for case_id in SYNTHETIC_GROUND_TRUTH_CONTROLS:
        case = by_id[case_id]
        # These are validated ground truth, not wild captures.
        assert case.source.provenance_tier == "synthetic"
        result = audit_case(case)
        assert result.expected_failure_modes == []
        assert result.detected_failure_modes == []
        assert result.passed


def test_report_generation() -> None:
    cases = load_benchmark_cases(ROOT)
    synthetic = next(case for case in cases if case.case_id == "syn-fm07-0001")
    result = audit_case(synthetic)

    report_path = write_markdown_report(result, ROOT / "reports")

    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "Audit Report: syn-fm07-0001" in text
    assert "FM-07" in text
