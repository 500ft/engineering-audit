"""The scaffold's oracle must keep reproducing its committed oracle.json.

SOLIDWORKS cannot run in CI, so the authoring half of the scaffold is not
exercised here. What CI can hold is the reference the host run is gated against:
if geometry.json or oracle.py drifts, oracle.json stops matching and the gate
quietly weakens against a number nobody recomputed.

It also checks that each re-drive case is capable of detecting anything. A case
whose expected volume equals the baseline would pass against a part whose
equations drive nothing, which is the one failure the re-drive exists to catch.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCAFFOLD = Path(__file__).resolve().parents[1] / "cadloop" / "scaffold"
COMMITTED = json.loads((SCAFFOLD / "oracle.json").read_text())
TOLERANCE_REL = 1e-9


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory: pytest.TempPathFactory) -> dict:
    pytest.importorskip("cadquery")
    out = tmp_path_factory.mktemp("oracle") / "oracle.json"
    subprocess.run(
        [sys.executable, str(SCAFFOLD / "oracle.py"),
         "--geometry", str(SCAFFOLD / "geometry.json"),
         "--redrive", str(SCAFFOLD / "redrive.json"),
         "--out", str(out)],
        check=True, capture_output=True,
    )
    return json.loads(out.read_text())


def relative(measured: float, expected: float) -> float:
    return abs(measured - expected) / expected


def test_baseline_part_matches_the_committed_oracle(regenerated: dict) -> None:
    got = regenerated["parts"]["mounting_plate"]
    want = COMMITTED["parts"]["mounting_plate"]
    assert got["n_solids"] == want["n_solids"]
    assert relative(got["volume_mm3"], want["volume_mm3"]) <= TOLERANCE_REL
    for axis, (a, b) in enumerate(zip(got["bbox_mm"], want["bbox_mm"])):
        assert a == pytest.approx(b, abs=1e-9), "bbox axis %d" % axis


def test_redrive_cases_match_the_committed_oracle(regenerated: dict) -> None:
    got = {case["name"]: case for case in regenerated["redrive"]}
    want = {case["name"]: case for case in COMMITTED["redrive"]}
    assert set(got) == set(want)
    for name, case in want.items():
        assert got[name]["globals"] == case["globals"], name
        assert relative(got[name]["expected"]["volume_mm3"],
                        case["expected"]["volume_mm3"]) <= TOLERANCE_REL, name


@pytest.mark.parametrize("case", COMMITTED["redrive"], ids=lambda c: c["name"])
def test_every_redrive_case_can_detect_inert_equations(case: dict) -> None:
    """A case whose volume equals the baseline proves nothing about parametricity."""
    baseline = COMMITTED["parts"]["mounting_plate"]["volume_mm3"]
    changed = case["expected"]["volume_mm3"]
    assert relative(changed, baseline) > 1e-3, (
        "%s changes the volume by too little to distinguish a driven part from "
        "one whose equations drive nothing" % case["name"]
    )


def test_redrive_globals_are_declared_by_the_authoring_script() -> None:
    """A case naming a variable the part does not declare would silently no-op."""
    authored = (SCAFFOLD / "author_part.py").read_text()
    for case in COMMITTED["redrive"]:
        for variable in case["globals"]:
            assert '"%s"' % variable in authored, (
                "%s is re-driven but never declared in author_part.py" % variable)
