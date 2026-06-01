from __future__ import annotations

from pathlib import Path

from mechaudit.case_loader import load_benchmark_cases, split_cases
from mechaudit.pressure_vessel import audit_case, within_tolerance
from mechaudit.report_writer import write_markdown_report


ROOT = Path(__file__).resolve().parents[1]


def test_loads_synthetic_cases_and_skips_pending_real_cases() -> None:
    cases = load_benchmark_cases(ROOT)
    complete, skipped = split_cases(cases)

    synthetic = [case for case in complete if case.source_type == "synthetic"]

    assert len(synthetic) == 5
    assert len(skipped) == 5
    assert {case.status for case in skipped} == {"pending_capture"}


def test_synthetic_cases_detect_expected_failure_modes() -> None:
    cases = load_benchmark_cases(ROOT)
    complete, _ = split_cases(cases)
    synthetic = [case for case in complete if case.source_type == "synthetic"]

    expected = {
        "syn-fm01-0001": ["FM-01"],
        "syn-fm02a-0001": ["FM-02A"],
        "syn-fm02b-0001": ["FM-02B"],
        "syn-arith-0001": ["FM-03"],
        "syn-fm07-0001": ["FM-07"],
    }

    results = {case.case_id: audit_case(case) for case in synthetic}

    assert set(results) == set(expected)
    for case_id, modes in expected.items():
        assert results[case_id].detected_failure_modes == modes
        assert results[case_id].passed


def test_tolerance_comparison() -> None:
    assert within_tolerance(100.4, 100.0, relative=0.005)
    assert not within_tolerance(101.0, 100.0, relative=0.005)


def test_report_generation() -> None:
    cases = load_benchmark_cases(ROOT)
    synthetic = next(case for case in cases if case.case_id == "syn-fm07-0001")
    result = audit_case(synthetic)

    report_path = write_markdown_report(result, ROOT / "reports")

    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "Audit Report: syn-fm07-0001" in text
    assert "FM-07" in text
