from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


class CaseLoadError(ValueError):
    """Controlled loader failure for malformed benchmark metadata."""

    failure_mode = "P-01"

    def __init__(self, path: Path, message: str):
        super().__init__(f"{self.failure_mode}: {path}: {message}")
        self.path = path
        self.message = message


class QuantityValue(BaseModel):
    value: float
    unit: str


class FormulaRecord(BaseModel):
    id: str
    formula_id: str | None = None
    equation: str
    purpose: str
    variables: dict[str, str] = Field(default_factory=dict)


class OutputRecord(BaseModel):
    name: str
    symbol: str
    value: float
    unit: str | None = None
    source: str


class ExpectedResult(BaseModel):
    value: float | None = None
    unit: str | None = None
    method: str
    required_assumptions: list[str] = Field(default_factory=list)


class ToleranceSpec(BaseModel):
    relative: float | None = 0.005
    absolute: float | None = None
    policy: str | None = None


class Notes(BaseModel):
    assumptions_stated: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reviewer_notes: str = ""
    expected_verifier_behavior: str = ""


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_id: str
    schema_version: str
    source_type: str
    status: str
    prompt_id: str
    failure_modes: list[str]
    formulas_used: list[FormulaRecord] = Field(default_factory=list)
    inputs: dict[str, QuantityValue] = Field(default_factory=dict)
    outputs: list[OutputRecord] = Field(default_factory=list)
    expected_result: ExpectedResult
    tolerance: ToleranceSpec = Field(default_factory=ToleranceSpec)
    notes: Notes = Field(default_factory=Notes)
    source_path: Path

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


def parse_first_json_block(markdown: str, path: Path) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(markdown)
    if not match:
        raise CaseLoadError(path, "No fenced JSON metadata block found.")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise CaseLoadError(path, f"Malformed JSON metadata: {exc.msg}.") from exc


def load_case_file(path: Path) -> BenchmarkCase:
    data = parse_first_json_block(path.read_text(encoding="utf-8"), path)
    data["source_path"] = path
    try:
        return BenchmarkCase.model_validate(data)
    except ValidationError as exc:
        raise CaseLoadError(path, f"Schema validation failed: {exc.errors()[0]['msg']}.") from exc


def load_benchmark_cases(root: Path) -> list[BenchmarkCase]:
    return [
        load_case_file(path)
        for path in sorted(root.glob("benchmark/**/*.md"))
        if path.name != "README.md" and path.name != "TEMPLATE.md"
    ]


def split_cases(cases: list[BenchmarkCase]) -> tuple[list[BenchmarkCase], list[BenchmarkCase]]:
    complete = [case for case in cases if case.status == "complete"]
    skipped = [case for case in cases if case.status == "pending_capture"]
    return complete, skipped
