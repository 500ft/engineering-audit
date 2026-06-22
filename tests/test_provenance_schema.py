from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mechaudit.case_loader import (
    CaseLoadError,
    load_case_file,
    verify_artifact_integrity,
)


def _gold_real_world_case() -> dict:
    """A structurally valid schema 0.3.0 gold real_world case."""
    return {
        "case_id": "rw-test-gold-0001",
        "schema_version": "0.3.0",
        "source_type": "real_world",
        "status": "complete",
        "source": {
            "kind": "manual_model_run",
            "description": "Verbatim test capture.",
            "provenance_tier": "gold",
            "raw_output_available": True,
            "capture_protocol": "standard",
            "artifacts": [
                {
                    "kind": "api_response",
                    "path": "raw/rw-test-gold-0001.txt",
                    "sha256": "placeholder",
                }
            ],
            "provider": "test",
            "model_name": "TestModel",
            "metadata_source": "api",
        },
        "prompt_id": "p1",
        "problem_statement": "test problem",
        "llm_response": {"prompt": "p", "response": "r"},
        "expected_result": {
            "value": None,
            "unit": None,
            "method": "test",
            "required_assumptions": [],
        },
        "failure_modes": [],
        "formulas_used": [],
        "inputs": {},
        "outputs": [],
        "units": {"system": "SI", "canonical_outputs": {}},
        "tolerance": {"relative": 0.005, "absolute": None},
        "notes": {},
    }


def _write_case(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / f"{data['case_id']}.md"
    path.write_text(
        "# test\n\n```json\n" + json.dumps(data) + "\n```\n",
        encoding="utf-8",
    )
    return path


def test_gold_case_loads_and_verifies_matching_artifact(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_bytes = b"verbatim model output"
    (raw_dir / "rw-test-gold-0001.txt").write_bytes(raw_bytes)

    data = _gold_real_world_case()
    data["source"]["artifacts"][0]["sha256"] = hashlib.sha256(raw_bytes).hexdigest()

    case = load_case_file(_write_case(tmp_path, data))
    verify_artifact_integrity(case, tmp_path)  # must not raise

    assert case.source.provenance_tier == "gold"


def test_unknown_top_level_key_is_p01(tmp_path: Path) -> None:
    data = _gold_real_world_case()
    data["unexpected_field"] = "boom"

    with pytest.raises(CaseLoadError) as exc_info:
        load_case_file(_write_case(tmp_path, data))
    assert exc_info.value.failure_mode == "P-01"


def test_unknown_schema_version_is_p01(tmp_path: Path) -> None:
    data = _gold_real_world_case()
    data["schema_version"] = "0.2.0"

    with pytest.raises(CaseLoadError) as exc_info:
        load_case_file(_write_case(tmp_path, data))
    assert exc_info.value.failure_mode == "P-01"


def test_complete_real_world_without_raw_artifact_is_p01(tmp_path: Path) -> None:
    data = _gold_real_world_case()
    data["source"]["artifacts"] = []

    with pytest.raises(CaseLoadError) as exc_info:
        load_case_file(_write_case(tmp_path, data))
    assert exc_info.value.failure_mode == "P-01"


def test_complete_real_world_without_raw_output_flag_is_p01(tmp_path: Path) -> None:
    data = _gold_real_world_case()
    data["source"]["raw_output_available"] = False

    with pytest.raises(CaseLoadError) as exc_info:
        load_case_file(_write_case(tmp_path, data))
    assert exc_info.value.failure_mode == "P-01"


def test_artifact_hash_mismatch_is_p01(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "rw-test-gold-0001.txt").write_bytes(b"actual bytes")

    data = _gold_real_world_case()
    data["source"]["artifacts"][0]["sha256"] = hashlib.sha256(b"different").hexdigest()

    case = load_case_file(_write_case(tmp_path, data))  # structure is valid
    with pytest.raises(CaseLoadError) as exc_info:
        verify_artifact_integrity(case, tmp_path)
    assert exc_info.value.failure_mode == "P-01"


def test_missing_artifact_file_is_p01(tmp_path: Path) -> None:
    data = _gold_real_world_case()
    data["source"]["artifacts"][0]["sha256"] = hashlib.sha256(b"x").hexdigest()

    case = load_case_file(_write_case(tmp_path, data))
    with pytest.raises(CaseLoadError) as exc_info:
        verify_artifact_integrity(case, tmp_path)  # file was never written
    assert exc_info.value.failure_mode == "P-01"


def test_pending_real_world_case_needs_no_artifact(tmp_path: Path) -> None:
    data = _gold_real_world_case()
    data["case_id"] = "rw-test-pending-0001"
    data["status"] = "pending_capture"
    data["source"] = {
        "kind": "manual_model_run",
        "description": "Pending capture slot.",
        "provenance_tier": None,
        "raw_output_available": False,
    }
    data["llm_response"] = {"prompt": "p", "response": ""}

    case = load_case_file(_write_case(tmp_path, data))
    verify_artifact_integrity(case, tmp_path)  # no artifacts -> no-op

    assert case.status == "pending_capture"
    assert case.source.provenance_tier is None
