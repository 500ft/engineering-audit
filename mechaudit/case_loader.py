from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

SCHEMA_VERSION = "0.3.0"

REAL_OUTPUT_ARTIFACT_KINDS = {"raw_response", "api_response"}


class CaseLoadError(ValueError):
    """Controlled loader failure for malformed benchmark metadata."""

    failure_mode = "P-01"

    def __init__(self, path: Path, message: str):
        super().__init__(f"{self.failure_mode}: {path}: {message}")
        self.path = path
        self.message = message


class QuantityValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float
    unit: str


class FormulaRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    formula_id: str | None = None
    equation: str
    purpose: str
    variables: dict[str, str] = Field(default_factory=dict)


ACCEPTED_CONVENTIONS = {
    "inner_radius",
    "mean_radius",
    "effective_radius_0p6t",
}


class OutputRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    symbol: str
    value: float
    unit: str | None = None
    source: str
    convention: str | None = None

    @field_validator("convention")
    @classmethod
    def validate_convention(cls, value: str | None) -> str | None:
        if value is not None and value not in ACCEPTED_CONVENTIONS:
            raise ValueError(f"Unsupported convention: {value}")
        return value


class ExpectedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None = None
    unit: str | None = None
    method: str
    required_assumptions: list[str] = Field(default_factory=list)


class ToleranceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative: float | None = 0.005
    absolute: float | None = None
    policy: str | None = None
    accepted_conventions: list[str] | None = None

    @field_validator("accepted_conventions")
    @classmethod
    def validate_accepted_conventions(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        unknown = sorted(set(value) - ACCEPTED_CONVENTIONS)
        if unknown:
            raise ValueError(f"Unsupported accepted_conventions: {unknown}")
        return value


class Notes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assumptions_stated: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reviewer_notes: str = ""
    expected_verifier_behavior: str = ""


class LlmResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str
    response: str


class Units(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system: str
    canonical_outputs: dict[str, str] = Field(default_factory=dict)


class ArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["raw_response", "api_response", "screenshot", "prompt"]
    path: str
    sha256: str
    media_type: str | None = None


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "synthetic",
        "manual_model_run",
        "api_model_run",
        "reviewer_synthesis",
        "coursework_transcript",
    ]
    description: str
    provenance_tier: Literal["gold", "silver", "deprecated", "synthetic"] | None = None
    raw_output_available: bool
    capture_protocol: Literal["standard", "challenge", "organic"] | None = None
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    provider: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    run_date: str | None = None
    temperature: float | None = None
    reasoning_effort: str | None = None
    run_settings: dict[str, Any] = Field(default_factory=dict)
    metadata_source: Literal["api", "self_report"] | None = None


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    schema_version: str
    source_type: Literal["synthetic", "real_world", "reference_correct"]
    status: Literal["complete", "pending_capture", "needs_review"]
    source: SourceRecord
    prompt_id: str
    problem_statement: str
    llm_response: LlmResponse
    expected_result: ExpectedResult
    failure_modes: list[str]
    formulas_used: list[FormulaRecord] = Field(default_factory=list)
    inputs: dict[str, QuantityValue] = Field(default_factory=dict)
    outputs: list[OutputRecord] = Field(default_factory=list)
    units: Units
    tolerance: ToleranceSpec = Field(default_factory=ToleranceSpec)
    notes: Notes = Field(default_factory=Notes)
    source_path: Path

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema_version {value!r}; expected {SCHEMA_VERSION!r}."
            )
        return value

    @field_validator("inputs", mode="before")
    @classmethod
    def normalize_inputs(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return {cls._canonical_input_name(key): val for key, val in value.items()}
        if isinstance(value, list):
            normalized: dict[str, Any] = {}
            for item in value:
                if not isinstance(item, dict) or "name" not in item:
                    continue
                key = cls._canonical_input_name(str(item["name"]))
                normalized[key] = {
                    "value": item["value"],
                    "unit": item["unit"],
                }
            return normalized
        return {}

    @staticmethod
    def _canonical_input_name(name: str) -> str:
        return {
            "wall_thickness": "thickness",
            "wall thickness": "thickness",
            "thickness": "thickness",
            "yield strength": "yield_strength",
        }.get(name, name)

    @model_validator(mode="after")
    def validate_provenance_coherence(self) -> "BenchmarkCase":
        source = self.source
        tier = source.provenance_tier

        if self.source_type == "synthetic":
            if tier != "synthetic":
                raise ValueError("synthetic cases require provenance_tier 'synthetic'.")
            if source.kind != "synthetic":
                raise ValueError("synthetic cases require source.kind 'synthetic'.")
            if source.model_name is not None:
                raise ValueError("synthetic cases must set source.model_name to null.")

        if self.source_type == "reference_correct":
            if tier != "deprecated":
                raise ValueError(
                    "reference_correct cases require provenance_tier 'deprecated'."
                )
            if source.kind != "reviewer_synthesis":
                raise ValueError(
                    "reference_correct cases require source.kind 'reviewer_synthesis'."
                )

        if self.source_type == "real_world" and self.status == "complete":
            if tier not in {"gold", "silver"}:
                raise ValueError(
                    "complete real_world cases require gold or silver provenance_tier."
                )
            if not source.raw_output_available:
                raise ValueError(
                    "complete real_world cases require raw_output_available true."
                )
            has_raw_artifact = any(
                artifact.kind in REAL_OUTPUT_ARTIFACT_KINDS
                for artifact in source.artifacts
            )
            if not has_raw_artifact:
                raise ValueError(
                    "complete real_world cases require a raw_response or api_response artifact."
                )

        return self


def parse_first_json_block(markdown: str, path: Path) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(markdown)
    if not match:
        raise CaseLoadError(path, "No fenced JSON metadata block found.")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise CaseLoadError(path, f"Malformed JSON metadata: {exc.msg}.") from exc


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def verify_artifact_integrity(case: BenchmarkCase, root: Path) -> None:
    """Confirm every referenced raw artifact exists and matches its recorded hash."""
    for artifact in case.source.artifacts:
        artifact_path = root / artifact.path
        if not artifact_path.is_file():
            raise CaseLoadError(
                case.source_path,
                f"Artifact file is missing: {artifact.path}.",
            )
        actual = _sha256_of(artifact_path)
        if actual != artifact.sha256.lower():
            raise CaseLoadError(
                case.source_path,
                f"Artifact hash mismatch for {artifact.path}: "
                f"expected {artifact.sha256}, found {actual}.",
            )


def load_case_file(path: Path) -> BenchmarkCase:
    data = parse_first_json_block(path.read_text(encoding="utf-8"), path)
    data["source_path"] = path
    try:
        return BenchmarkCase.model_validate(data)
    except ValidationError as exc:
        raise CaseLoadError(path, f"Schema validation failed: {exc.errors()[0]['msg']}.") from exc


def load_benchmark_cases(root: Path) -> list[BenchmarkCase]:
    cases = [
        load_case_file(path)
        for path in sorted(root.glob("benchmark/**/*.md"))
        if path.name != "README.md" and path.name != "TEMPLATE.md"
    ]
    for case in cases:
        verify_artifact_integrity(case, root)
    return cases


def split_cases(cases: list[BenchmarkCase]) -> tuple[list[BenchmarkCase], list[BenchmarkCase]]:
    complete = [case for case in cases if case.status == "complete"]
    skipped = [case for case in cases if case.status == "pending_capture"]
    return complete, skipped
