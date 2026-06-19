from __future__ import annotations

from pathlib import Path

from mechaudit.case_loader import BenchmarkCase, QuantityValue, load_benchmark_cases
from mechaudit.pressure_vessel import audit_case


ROOT = Path(__file__).resolve().parents[1]


def _case(case_id: str) -> BenchmarkCase:
    return next(case for case in load_benchmark_cases(ROOT) if case.case_id == case_id)


def _detected(case: BenchmarkCase) -> set[str]:
    mutated = case.model_copy(deep=True)
    mutated.failure_modes = []
    return set(audit_case(mutated).detected_failure_modes)


def test_fm01_detection_is_computed_not_echoed_from_metadata() -> None:
    assert "FM-01" in _detected(_case("syn-fm01-0001"))


def test_fm02a_detection_uses_formula_id_not_metadata_label() -> None:
    case = _case("syn-fm07-0001").model_copy(deep=True)
    case.failure_modes = []
    case.formulas_used[0].formula_id = "longitudinal_stress_thin_wall"

    assert "FM-02A" in set(audit_case(case).detected_failure_modes)


def test_fm02b_detection_uses_thin_wall_ratio() -> None:
    case = _case("syn-fm07-0001").model_copy(deep=True)
    case.failure_modes = []
    case.inputs["thickness"] = QuantityValue(value=20, unit="mm")

    assert "FM-02B" in set(audit_case(case).detected_failure_modes)


def test_fm03_detection_uses_recomputed_final_value() -> None:
    assert "FM-03" in _detected(_case("syn-arith-0001"))


def test_fm03_allows_explicit_mean_radius_convention() -> None:
    case = _case("syn-fm07-0001").model_copy(deep=True)
    case.failure_modes = []
    case.tolerance.accepted_conventions = ["inner_radius", "mean_radius"]
    case.outputs = [
        output.model_copy(update={"value": 20.6})
        if output.source == "llm" and output.name == "hoop_stress_final"
        else output
        for output in case.outputs
        if output.name != "hoop_stress_substitution"
    ]

    assert "FM-03" not in set(audit_case(case).detected_failure_modes)


def test_fm03_still_flags_wrong_value_with_multiple_conventions() -> None:
    case = _case("syn-fm07-0001").model_copy(deep=True)
    case.failure_modes = []
    case.tolerance.accepted_conventions = ["inner_radius", "mean_radius"]
    case.outputs = [
        output.model_copy(update={"value": 22.0})
        if output.source == "llm" and output.name == "hoop_stress_final"
        else output
        for output in case.outputs
        if output.name != "hoop_stress_substitution"
    ]

    assert "FM-03" in set(audit_case(case).detected_failure_modes)


def test_fm03_default_convention_rejects_mean_radius() -> None:
    case = _case("syn-fm07-0001").model_copy(deep=True)
    case.failure_modes = []
    case.outputs = [
        output.model_copy(update={"value": 20.6})
        if output.source == "llm" and output.name == "hoop_stress_final"
        else output
        for output in case.outputs
        if output.name != "hoop_stress_substitution"
    ]

    assert "FM-03" in set(audit_case(case).detected_failure_modes)


def test_fm03_allows_effective_radius_heuristic_only_when_explicit() -> None:
    case = _case("syn-fm07-0001").model_copy(deep=True)
    case.failure_modes = []
    case.tolerance.accepted_conventions = ["effective_radius_0p6t"]
    case.outputs = [
        output.model_copy(update={"value": 20.72})
        if output.source == "llm" and output.name == "hoop_stress_final"
        else output
        for output in case.outputs
        if output.name != "hoop_stress_substitution"
    ]

    assert "FM-03" not in set(audit_case(case).detected_failure_modes)


def test_fm07_detection_uses_intermediate_reasoning_mismatch() -> None:
    assert "FM-07" in _detected(_case("syn-fm07-0001"))


def test_fm07_flags_cross_convention_reasoning_mismatch() -> None:
    case = _case("syn-fm07-0001").model_copy(deep=True)
    case.failure_modes = []
    case.tolerance.accepted_conventions = ["inner_radius", "mean_radius"]
    case.outputs = [
        output.model_copy(update={"value": 20.6})
        if output.source == "llm" and output.name == "hoop_stress_substitution"
        else output
        for output in case.outputs
    ]

    assert "FM-07" in set(audit_case(case).detected_failure_modes)
