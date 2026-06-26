"""Detection tests for the Kt-aware stress-concentration check (FM-04).

These exercise the verifier gap closed for finite-width holed-plate cases: the
verifier recomputes Kt_net, sigma_net and sigma_max from the inputs (via the
in-repo oracle) and flags FM-04 when the LLM's reported peak stress deviates
beyond tolerance, distinguishing "stress concentration omitted" (peak ==
sigma_net) from "wrong Kt or wrong nominal".

The guard that matters as much as detection: the `syn-kt-hole-0001` control and
any correctly-solved case must NOT flag FM-04 (false-positive regression).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mechaudit.case_loader import BenchmarkCase, load_benchmark_cases, load_case_file
from mechaudit.pressure_vessel import audit_case, compute_plate_with_hole


ROOT = Path(__file__).resolve().parents[1]

PROMOTED_FM04_CASES = (
    "rw-stress-concentration-claude-haiku-0001",  # concentration omitted + wrong area
    "rw-stress-concentration-claude-haiku-0002",  # wrong nominal (net area)
    "rw-stress-concentration-claude-haiku-0003",  # wrong Kt (infinite-plate 3.0)
    "rw-stress-concentration-codex-gpt54mini-0001",  # gross nominal with finite-width Kt
    "rw-stress-concentration-codex-gpt54mini-0002",  # gross-reference convention mismatch
    "rw-stress-concentration-codex-gpt55-0001",  # gross nominal with finite-width Kt
    "rw-stress-concentration-codex-gpt55-0002",  # gross-reference convention mismatch
)


def _case(case_id: str) -> BenchmarkCase:
    return next(c for c in load_benchmark_cases(ROOT) if c.case_id == case_id)


def _detected(case: BenchmarkCase) -> set[str]:
    mutated = case.model_copy(deep=True)
    mutated.failure_modes = []
    return set(audit_case(mutated).detected_failure_modes)


def _sc_check(case: BenchmarkCase):
    result = audit_case(case)
    return next(c for c in result.checks if c.name == "stress-concentration-peak")


# --- The oracle the check stands on ------------------------------------------


def test_compute_plate_with_hole_matches_oracle() -> None:
    case = _case("rw-stress-concentration-claude-haiku-0001")
    sc = compute_plate_with_hole(case)
    # W=60, t=6, d=12, P=18 kN -> d/W=0.2, Kt_net=2.51904, sigma_net=62.5
    assert sc["kt_net"] == pytest.approx(2.519040, abs=1e-6)
    assert sc["net_section_stress_MPa"] == pytest.approx(62.5)
    assert sc["peak_stress_MPa"] == pytest.approx(157.44, abs=1e-2)


# --- Detection on the promoted real captures ---------------------------------


@pytest.mark.parametrize("case_id", PROMOTED_FM04_CASES)
def test_promoted_real_world_cases_detect_fm04(case_id: str) -> None:
    case = _case(case_id)
    assert case.source_type == "real_world"
    assert case.source.provenance_tier == "gold"
    result = audit_case(case)
    assert "FM-04" in result.detected_failure_modes
    assert result.detected_failure_modes == ["FM-04"]
    assert result.passed
    # Detection is computed, not echoed from the case's own failure_modes.
    assert "FM-04" in _detected(case)


# --- Sub-case discrimination --------------------------------------------------


def test_omitted_concentration_subcase_names_the_missing_kt() -> None:
    # Force the reported peak to equal sigma_net exactly: the verifier should say
    # the concentration was omitted, not "wrong Kt".
    case = _case("rw-stress-concentration-claude-haiku-0001").model_copy(deep=True)
    case.failure_modes = []
    sigma_net = compute_plate_with_hole(case)["net_section_stress_MPa"]
    case.outputs = [
        o.model_copy(update={"value": sigma_net})
        if o.source == "llm" and o.name == "peak_stress"
        else o
        for o in case.outputs
    ]
    check = _sc_check(case)
    assert not check.passed
    assert check.detected_failure_mode == "FM-04"
    assert "omitted" in check.message.lower()


def test_wrong_kt_or_nominal_subcase_is_labeled_distinctly() -> None:
    # The promoted 0002 capture reports 315 MPa, matching neither sigma_net nor
    # sigma_max -> "wrong Kt or wrong nominal".
    check = _sc_check(_case("rw-stress-concentration-claude-haiku-0002"))
    assert not check.passed
    assert "wrong kt or wrong nominal" in check.message.lower()


# --- False-positive guards ----------------------------------------------------


def test_syn_kt_hole_control_does_not_flag_fm04() -> None:
    case = load_case_file(ROOT / "benchmark" / "synthetic" / "syn-kt-hole-0001.md")
    result = audit_case(case)
    assert "FM-04" not in result.detected_failure_modes
    assert result.detected_failure_modes == []
    assert _sc_check(case).passed
    # And detection is not merely echoing an empty metadata list.
    assert "FM-04" not in _detected(case)


def test_correctly_solved_holed_plate_is_clean() -> None:
    # Replace the reported peak with the validated sigma_max: no flag.
    case = _case("rw-stress-concentration-claude-haiku-0003").model_copy(deep=True)
    case.failure_modes = []
    sigma_max = compute_plate_with_hole(case)["peak_stress_MPa"]
    case.outputs = [
        o.model_copy(update={"value": sigma_max})
        if o.source == "llm" and o.name == "peak_stress"
        else o
        for o in case.outputs
    ]
    result = audit_case(case)
    assert "FM-04" not in result.detected_failure_modes
    assert _sc_check(case).passed


def test_pressure_vessel_and_axial_cases_do_not_trigger_kt_check() -> None:
    # The holed-plate path must not fire on unrelated problem classes.
    for case_id in ("rw-pressure-vessel-claude-0001", "syn-fm01-0001"):
        case = _case(case_id)
        result = audit_case(case)
        assert "FM-04" not in result.detected_failure_modes
        assert all(c.name != "stress-concentration-peak" for c in result.checks)
