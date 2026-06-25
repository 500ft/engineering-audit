"""Provenance-first capture harness for real model outputs.

This module is the rail on which genuine ``gold``/``silver`` captures will run.
It deliberately does **not** call any model API or network: the verbatim raw
output is supplied by the caller (via a file or stdin). The harness's job is to
turn a (prompt, model id, raw output) triple into an immutable, hash-verified
artifact plus a ``SourceRecord``-shaped provenance record, stored under a
``captures/`` tree with a pre-registered ``prompts/`` / ``models/`` / ``runs/``
structure.

Nothing here fabricates evidence. It only records and hashes what it is handed,
so that when the operator runs a real model later, capturing it is a single
command and the result is tamper-evident by construction.

The provenance record produced here is intentionally a subset of the benchmark
``source`` object documented in ``docs/schema_contract.md`` and
``docs/capture_provenance.md``: ``provenance_tier`` (``gold``/``silver``),
provider/model/version/date, run settings, ``raw_output_available``, and a typed
``artifacts`` list carrying the SHA-256 of the verbatim bytes. A captured run can
later be promoted into a ``complete`` ``real_world`` benchmark case by copying its
artifact into ``benchmark/real_world/raw/`` and referencing the recorded hash.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


CAPTURE_SCHEMA_VERSION = "capture-0.1.0"

# Tiers that represent a genuine, verbatim model capture. Reviewer synthesis and
# synthetic cases are never produced by this harness; it only records real bytes.
CaptureTier = Literal["gold", "silver"]
VALID_CAPTURE_TIERS: frozenset[str] = frozenset({"gold", "silver"})

# Mirrors ArtifactRecord.kind in case_loader, restricted to what a capture emits.
ArtifactKind = Literal["raw_response", "api_response", "screenshot", "prompt"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class CaptureError(ValueError):
    """Raised when a capture request is malformed or would overwrite an artifact."""


def sha256_hex(data: bytes) -> str:
    """Lowercase hex SHA-256 of ``data``. Deterministic by construction."""
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def slugify(value: str) -> str:
    """Normalize an identifier into a filesystem-safe lowercase slug."""
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    if not slug:
        raise CaptureError(f"Cannot derive a slug from {value!r}.")
    return slug


@dataclass(frozen=True)
class CaptureArtifact:
    """A single hashed file produced by a capture."""

    kind: ArtifactKind
    path: str
    sha256: str
    media_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "sha256": self.sha256,
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class SourceRecord:
    """Provenance record for one captured run.

    This is the capture-time analogue of the benchmark ``source`` object. Field
    names match ``docs/schema_contract.md`` so a record can be lifted into a
    benchmark case with no renaming.
    """

    capture_schema_version: str
    prompt_id: str
    prompt_sha256: str
    provider: str | None
    model_name: str
    model_version: str | None
    run_date: str
    provenance_tier: CaptureTier
    capture_protocol: Literal["standard", "challenge", "organic"]
    metadata_source: Literal["api", "self_report"]
    raw_output_available: bool
    captured_at: str
    artifacts: list[CaptureArtifact] = field(default_factory=list)
    temperature: float | None = None
    reasoning_effort: str | None = None
    run_settings: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_schema_version": self.capture_schema_version,
            "prompt_id": self.prompt_id,
            "prompt_sha256": self.prompt_sha256,
            "provider": self.provider,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "run_date": self.run_date,
            "provenance_tier": self.provenance_tier,
            "capture_protocol": self.capture_protocol,
            "metadata_source": self.metadata_source,
            "raw_output_available": self.raw_output_available,
            "captured_at": self.captured_at,
            "temperature": self.temperature,
            "reasoning_effort": self.reasoning_effort,
            "run_settings": self.run_settings,
            "notes": self.notes,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceRecord":
        artifacts = [
            CaptureArtifact(
                kind=item["kind"],
                path=item["path"],
                sha256=item["sha256"],
                media_type=item.get("media_type"),
            )
            for item in data.get("artifacts", [])
        ]
        return cls(
            capture_schema_version=data["capture_schema_version"],
            prompt_id=data["prompt_id"],
            prompt_sha256=data["prompt_sha256"],
            provider=data.get("provider"),
            model_name=data["model_name"],
            model_version=data.get("model_version"),
            run_date=data["run_date"],
            provenance_tier=data["provenance_tier"],
            capture_protocol=data["capture_protocol"],
            metadata_source=data["metadata_source"],
            raw_output_available=data["raw_output_available"],
            captured_at=data["captured_at"],
            artifacts=artifacts,
            temperature=data.get("temperature"),
            reasoning_effort=data.get("reasoning_effort"),
            run_settings=data.get("run_settings", {}),
            notes=data.get("notes", ""),
        )


@dataclass(frozen=True)
class CaptureResult:
    """Everything written for one capture, returned for inspection/testing."""

    run_id: str
    run_dir: Path
    record_path: Path
    record: SourceRecord


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_capture_layout(root: Path) -> dict[str, Path]:
    """Pre-register the captures/ structure: prompts/, models/, runs/.

    Idempotent. Returns the three subdirectory paths.
    """
    captures = root / "captures"
    layout = {
        "captures": captures,
        "prompts": captures / "prompts",
        "models": captures / "models",
        "runs": captures / "runs",
    }
    for path in layout.values():
        path.mkdir(parents=True, exist_ok=True)
    readme = captures / "README.md"
    if not readme.exists():
        readme.write_text(_CAPTURES_README, encoding="utf-8")
    return layout


def register_prompt(root: Path, prompt_id: str, prompt_text: str) -> CaptureArtifact:
    """Store the verbatim prompt under captures/prompts/ keyed by content hash.

    Storing by ``prompt_id`` is deterministic; re-registering identical text is a
    no-op, and re-registering *different* text under the same id is refused so a
    prompt cannot be silently rewritten after runs reference it.
    """
    layout = ensure_capture_layout(root)
    prompt_bytes = prompt_text.encode("utf-8")
    digest = sha256_hex(prompt_bytes)
    rel = f"captures/prompts/{slugify(prompt_id)}.txt"
    dest = root / rel
    if dest.exists():
        existing = sha256_hex(dest.read_bytes())
        if existing != digest:
            raise CaptureError(
                f"Prompt id {prompt_id!r} already registered with different text "
                f"(stored {existing}, new {digest}). Use a new prompt_id."
            )
    else:
        dest.write_bytes(prompt_bytes)
    _ = layout  # layout creation is the side effect we needed
    return CaptureArtifact(
        kind="prompt", path=rel, sha256=digest, media_type="text/plain"
    )


def _register_model(root: Path, model_name: str, model_version: str | None) -> None:
    """Record that a model id has been seen, under captures/models/."""
    layout = ensure_capture_layout(root)
    rel = layout["models"] / f"{slugify(model_name)}.json"
    payload = {
        "model_name": model_name,
        "model_version": model_version,
        "first_seen": _utc_now_iso(),
    }
    if not rel.exists():
        rel.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_run_id(model_name: str, prompt_id: str, output_sha256: str) -> str:
    """Deterministic run id from model, prompt, and verbatim output hash.

    Keying on the output hash means the same bytes always land in the same run
    directory, and *different* bytes never collide.
    """
    return f"{slugify(model_name)}__{slugify(prompt_id)}__{output_sha256[:12]}"


def capture_run(
    root: Path,
    *,
    prompt_id: str,
    prompt_text: str,
    model_name: str,
    raw_output: bytes,
    run_date: str,
    provider: str | None = None,
    model_version: str | None = None,
    provenance_tier: CaptureTier = "gold",
    capture_protocol: Literal["standard", "challenge", "organic"] = "standard",
    metadata_source: Literal["api", "self_report"] = "api",
    output_kind: ArtifactKind = "raw_response",
    output_media_type: str | None = "text/plain",
    temperature: float | None = None,
    reasoning_effort: str | None = None,
    run_settings: dict[str, Any] | None = None,
    notes: str = "",
    overwrite: bool = False,
) -> CaptureResult:
    """Capture one verbatim model output as an immutable, hash-verified artifact.

    ``raw_output`` is bytes already in hand (read from a file or stdin) — this
    function never fetches anything. It hashes the verbatim bytes, writes them
    under ``captures/runs/<run_id>/``, registers the prompt and model, and writes
    a ``source.json`` provenance record alongside.

    Re-capturing identical bytes is idempotent. Re-capturing into an existing run
    directory with *different* bytes is refused unless ``overwrite=True``.
    """
    if provenance_tier not in VALID_CAPTURE_TIERS:
        raise CaptureError(
            f"provenance_tier must be one of {sorted(VALID_CAPTURE_TIERS)}; "
            f"got {provenance_tier!r}. The capture harness only records genuine "
            f"verbatim runs, never synthetic or reviewer-synthesis tiers."
        )
    if not raw_output:
        raise CaptureError("raw_output is empty; refusing to capture an empty artifact.")
    if not run_date:
        raise CaptureError("run_date is required (ISO date of the model run).")

    ensure_capture_layout(root)
    prompt_artifact = register_prompt(root, prompt_id, prompt_text)
    _register_model(root, model_name, model_version)

    output_sha = sha256_hex(raw_output)
    run_id = build_run_id(model_name, prompt_id, output_sha)
    run_dir = root / "captures" / "runs" / run_id

    suffix = ".json" if output_kind == "api_response" else ".txt"
    output_rel = f"captures/runs/{run_id}/output{suffix}"
    output_path = root / output_rel

    if output_path.exists():
        existing = sha256_hex(output_path.read_bytes())
        if existing != output_sha and not overwrite:
            raise CaptureError(
                f"Run {run_id} already holds different output bytes "
                f"(stored {existing}, new {output_sha}). Pass overwrite=True to replace."
            )

    run_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw_output)

    output_artifact = CaptureArtifact(
        kind=output_kind,
        path=output_rel,
        sha256=output_sha,
        media_type=output_media_type,
    )

    record = SourceRecord(
        capture_schema_version=CAPTURE_SCHEMA_VERSION,
        prompt_id=prompt_id,
        prompt_sha256=prompt_artifact.sha256,
        provider=provider,
        model_name=model_name,
        model_version=model_version,
        run_date=run_date,
        provenance_tier=provenance_tier,
        capture_protocol=capture_protocol,
        metadata_source=metadata_source,
        raw_output_available=True,
        captured_at=_utc_now_iso(),
        artifacts=[output_artifact, prompt_artifact],
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        run_settings=dict(run_settings or {}),
        notes=notes,
    )

    record_path = run_dir / "source.json"
    record_path.write_text(record.to_json(), encoding="utf-8")

    return CaptureResult(
        run_id=run_id,
        run_dir=run_dir,
        record_path=record_path,
        record=record,
    )


def verify_capture(root: Path, run_id: str) -> SourceRecord:
    """Reload a stored capture and confirm every artifact matches its hash.

    Raises :class:`CaptureError` (the capture-layer analogue of ``P-01``) if the
    record is missing, an artifact file is absent, or any byte has changed since
    capture. This makes "the raw output is present and unmodified" a checked
    property, exactly as the benchmark loader does for ``real_world`` cases.
    """
    record_path = root / "captures" / "runs" / run_id / "source.json"
    if not record_path.is_file():
        raise CaptureError(f"No capture record at {record_path}.")
    record = SourceRecord.from_dict(json.loads(record_path.read_text(encoding="utf-8")))
    for artifact in record.artifacts:
        artifact_path = root / artifact.path
        if not artifact_path.is_file():
            raise CaptureError(f"Capture artifact missing: {artifact.path}.")
        actual = sha256_hex(artifact_path.read_bytes())
        if actual != artifact.sha256.lower():
            raise CaptureError(
                f"Capture artifact hash mismatch for {artifact.path}: "
                f"expected {artifact.sha256}, found {actual}."
            )
    return record


_CAPTURES_README = """\
# Captures

Immutable, hash-verified raw model captures. This tree is the rail for genuine
`gold`/`silver` captures; nothing here is fabricated or synthetic.

Layout (pre-registered by `mechaudit.capture`):

- `prompts/` — verbatim prompt text, one file per `prompt_id`. Re-registering a
  prompt id with different text is refused.
- `models/`  — one record per model id seen.
- `runs/`    — one directory per captured run, named
  `<model>__<prompt>__<output-hash12>`, holding the verbatim `output.txt`
  (or `output.json`) and a `source.json` provenance record with the SHA-256 of
  the captured bytes.

A captured run is promoted into a `complete` `real_world` benchmark case by
copying its output artifact into `benchmark/real_world/raw/` and referencing the
recorded hash from the case `source.artifacts[]`. See `docs/capture_provenance.md`.

The actual model API call that produces `output.txt` is performed by the
operator with their own credentials; `mechaudit capture` only records the bytes
it is handed (from a file or stdin) and never performs network access.
"""
