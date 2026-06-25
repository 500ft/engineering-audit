from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mechaudit.capture import (
    CaptureError,
    SourceRecord,
    build_run_id,
    capture_run,
    ensure_capture_layout,
    register_prompt,
    sha256_hex,
    verify_capture,
)


PROMPT = "Solve the pressure vessel problem and show your work."
RAW = b"sigma_h = p r / t = 1.2 * 50 / 3 = 20.0 MPa\n"


def _capture(root: Path, raw: bytes = RAW, **overrides) -> "object":
    kwargs = dict(
        prompt_id="pressure_vessel_prompt_v1",
        prompt_text=PROMPT,
        model_name="gpt-5",
        raw_output=raw,
        run_date="2026-06-25",
        provider="openai",
        model_version="gpt-5-2026-06",
    )
    kwargs.update(overrides)
    return capture_run(root, **kwargs)


def test_sha256_is_deterministic() -> None:
    assert sha256_hex(RAW) == sha256_hex(RAW)
    assert sha256_hex(RAW) == hashlib.sha256(RAW).hexdigest()
    assert sha256_hex(b"a") != sha256_hex(b"b")


def test_capture_layout_is_preregistered_and_idempotent(tmp_path: Path) -> None:
    layout = ensure_capture_layout(tmp_path)
    for key in ("prompts", "models", "runs"):
        assert layout[key].is_dir()
    # Idempotent second call.
    ensure_capture_layout(tmp_path)
    assert (tmp_path / "captures" / "README.md").exists()


def test_capture_records_verbatim_output_hash(tmp_path: Path) -> None:
    result = _capture(tmp_path)

    output_artifact = next(
        a for a in result.record.artifacts if a.kind == "raw_response"
    )
    assert output_artifact.sha256 == hashlib.sha256(RAW).hexdigest()

    stored = (tmp_path / output_artifact.path).read_bytes()
    assert stored == RAW  # bytes are verbatim, unmodified
    assert result.record.raw_output_available is True
    assert result.record.provenance_tier == "gold"


def test_capture_writes_preregistered_structure(tmp_path: Path) -> None:
    result = _capture(tmp_path)

    assert (tmp_path / "captures" / "prompts" / "pressure-vessel-prompt-v1.txt").exists()
    assert (tmp_path / "captures" / "models" / "gpt-5.json").exists()
    assert result.run_dir.is_dir()
    assert result.record_path.exists()
    assert result.record_path.name == "source.json"


def test_provenance_record_round_trips(tmp_path: Path) -> None:
    result = _capture(tmp_path)

    on_disk = json.loads(result.record_path.read_text(encoding="utf-8"))
    reloaded = SourceRecord.from_dict(on_disk)

    assert reloaded == result.record
    # Field names match the benchmark source contract so a record can be lifted in.
    assert on_disk["provenance_tier"] == "gold"
    assert on_disk["prompt_sha256"] == hashlib.sha256(PROMPT.encode()).hexdigest()
    assert on_disk["artifacts"][0]["sha256"] == hashlib.sha256(RAW).hexdigest()


def test_run_id_is_deterministic_for_same_bytes(tmp_path: Path) -> None:
    out_hash = sha256_hex(RAW)
    expected = build_run_id("gpt-5", "pressure_vessel_prompt_v1", out_hash)

    first = _capture(tmp_path)
    second = _capture(tmp_path)  # identical bytes -> idempotent

    assert first.run_id == expected
    assert second.run_id == first.run_id


def test_verify_capture_passes_for_untouched_artifacts(tmp_path: Path) -> None:
    result = _capture(tmp_path)
    record = verify_capture(tmp_path, result.run_id)  # must not raise
    assert record.prompt_id == "pressure_vessel_prompt_v1"


def test_verify_capture_detects_tampering(tmp_path: Path) -> None:
    result = _capture(tmp_path)
    output_artifact = next(
        a for a in result.record.artifacts if a.kind == "raw_response"
    )
    (tmp_path / output_artifact.path).write_bytes(b"tampered output")

    with pytest.raises(CaptureError):
        verify_capture(tmp_path, result.run_id)


def test_verify_capture_detects_missing_artifact(tmp_path: Path) -> None:
    result = _capture(tmp_path)
    output_artifact = next(
        a for a in result.record.artifacts if a.kind == "raw_response"
    )
    (tmp_path / output_artifact.path).unlink()

    with pytest.raises(CaptureError):
        verify_capture(tmp_path, result.run_id)


def test_capture_rejects_synthetic_tier(tmp_path: Path) -> None:
    with pytest.raises(CaptureError):
        _capture(tmp_path, provenance_tier="synthetic")  # type: ignore[arg-type]


def test_capture_rejects_empty_output(tmp_path: Path) -> None:
    with pytest.raises(CaptureError):
        _capture(tmp_path, raw=b"")


def test_prompt_id_cannot_be_silently_rewritten(tmp_path: Path) -> None:
    register_prompt(tmp_path, "pressure_vessel_prompt_v1", PROMPT)
    # Same text re-registers cleanly.
    register_prompt(tmp_path, "pressure_vessel_prompt_v1", PROMPT)
    # Different text under the same id is refused.
    with pytest.raises(CaptureError):
        register_prompt(tmp_path, "pressure_vessel_prompt_v1", PROMPT + " changed")


def test_different_output_bytes_do_not_collide(tmp_path: Path) -> None:
    first = _capture(tmp_path, raw=b"answer A\n")
    second = _capture(tmp_path, raw=b"answer B\n")
    assert first.run_id != second.run_id
    assert first.run_dir != second.run_dir


def test_recapture_with_different_bytes_into_same_run_is_refused(tmp_path: Path) -> None:
    # Force a run-id collision by reusing the same output hash directory while
    # changing the stored bytes underneath it.
    result = _capture(tmp_path)
    output_artifact = next(
        a for a in result.record.artifacts if a.kind == "raw_response"
    )
    (tmp_path / output_artifact.path).write_bytes(b"different bytes now")

    with pytest.raises(CaptureError):
        _capture(tmp_path)  # same run_id, but on-disk bytes differ -> refused

    # overwrite=True heals it.
    healed = _capture(tmp_path, overwrite=True)
    assert (tmp_path / output_artifact.path).read_bytes() == RAW
    assert healed.run_id == result.run_id
