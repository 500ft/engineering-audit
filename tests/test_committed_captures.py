from __future__ import annotations

import json
from pathlib import Path

from mechaudit.capture import verify_capture


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_RUNS = ROOT / "captures" / "runs"
EXPECTED_CAPTURE_COUNTS_BY_MODEL = {
    "claude-haiku-4-5-20251001": 10,
    "gpt-5.4-mini": 10,
    "gpt-5.5": 10,
}


def test_all_committed_capture_runs_are_hash_verified() -> None:
    run_dirs = sorted(path for path in CAPTURE_RUNS.iterdir() if path.is_dir())

    counts_by_model = dict.fromkeys(EXPECTED_CAPTURE_COUNTS_BY_MODEL, 0)

    for run_dir in run_dirs:
        record = verify_capture(ROOT, run_dir.name)
        counts_by_model[record.model_name] = counts_by_model.get(record.model_name, 0) + 1
        assert record.provenance_tier == "gold"
        assert record.raw_output_available is True
        assert record.capture_protocol == "challenge"
        assert record.metadata_source == "self_report"
        assert any(artifact.kind == "raw_response" for artifact in record.artifacts)
        assert any(artifact.kind == "prompt" for artifact in record.artifacts)

    assert counts_by_model == EXPECTED_CAPTURE_COUNTS_BY_MODEL


def test_committed_capture_source_records_point_to_their_own_run_directory() -> None:
    for source_path in sorted(CAPTURE_RUNS.glob("*/source.json")):
        data = json.loads(source_path.read_text(encoding="utf-8"))
        raw_artifacts = [
            artifact for artifact in data["artifacts"] if artifact["kind"] == "raw_response"
        ]

        assert len(raw_artifacts) == 1
        assert raw_artifacts[0]["path"] == f"captures/runs/{source_path.parent.name}/output.txt"
