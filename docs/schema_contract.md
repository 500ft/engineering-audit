# Schema Contract

This document defines the structured data contract MechAudit benchmark files
and verifier code consume. As of `0.3.0` the loader validates the **full**
contract with Pydantic and rejects unknown keys (`extra = "forbid"`). There is
no permissive provenance area: every field below is modeled, and any field not
listed here causes a `P-01` load failure.

## Version

Current schema version: `0.3.0`. The loader accepts **only** `0.3.0`; any other
`schema_version` is reported as `P-01`. There is no backward-compatible reader
for `0.2.0`.

Schema versions use semantic versioning:

- Patch changes clarify wording or examples without changing fields.
- Minor changes add optional fields.
- Major changes rename fields, remove fields, or change required semantics.

The `0.2.0` to `0.3.0` change is major: provider/run provenance moved from
top-level keys into the `source` object, `source` gained `provenance_tier` and a
typed `artifacts` list, `source_type` gained `reference_correct`, and unknown
keys are now rejected.

## Benchmark File Format

Benchmark cases are Markdown files with a fenced `json` metadata block near the
top. The Markdown makes cases readable in GitHub; the JSON block gives the
future verifier a stable parse target.

## Required Top-Level Fields

| Field | Type | Required | Description |
|---|---:|---:|---|
| `case_id` | string | yes | Stable benchmark identifier. |
| `schema_version` | string | yes | Must be `0.3.0`. |
| `source_type` | string | yes | One of `synthetic`, `real_world`, or `reference_correct`. |
| `status` | string | yes | One of `complete`, `pending_capture`, or `needs_review`. |
| `source` | object | yes | Provenance, capture source, and raw artifacts. |
| `prompt_id` | string | yes | Stable prompt identifier. |
| `problem_statement` | string | yes | Original engineering problem. |
| `llm_response` | object | yes | Prompt and raw model response being audited. |
| `expected_result` | object | yes | Trusted answer or trusted method. |
| `failure_modes` | array | yes | Expected labels from the taxonomy. |
| `formulas_used` | array | yes | Formula records stated by the LLM or expected solution. |
| `inputs` | object or array | yes | Named numerical inputs with units. Array form is normalized to object form on load. |
| `outputs` | array | yes | Named numerical outputs with units. |
| `units` | object | yes | Unit system and canonical units. |
| `tolerance` | object | yes | Numeric tolerance policy for the case. |
| `notes` | object | yes | Assumptions, limitations, and reviewer notes. |

Model and run provenance (`model_name`, `model_version`, `run_date`,
`temperature`, `run_settings`, `metadata_source`, `reasoning_effort`) are no
longer top-level fields; they live inside `source`.

## Field Details

### `source`

| Field | Type | Required | Description |
|---|---:|---:|---|
| `kind` | string | yes | `synthetic`, `manual_model_run`, `api_model_run`, `reviewer_synthesis`, or `coursework_transcript`. |
| `description` | string | yes | Human-readable provenance. |
| `provenance_tier` | string or null | yes | `gold`, `silver`, `deprecated`, `synthetic`, or `null` for pending captures. See `docs/capture_provenance.md`. |
| `raw_output_available` | boolean | yes | Whether a verbatim artifact is present. |
| `capture_protocol` | string or null | no | `standard`, `challenge`, or `organic`. |
| `artifacts` | array | no | Typed raw artifacts (see below). Required to be non-empty for `complete` `real_world` cases. |
| `provider` | string or null | no | Provider/vendor. |
| `model_name` | string or null | no | Model product name; `null` for synthetic cases. |
| `model_version` | string or null | no | Model version or release identifier. |
| `run_date` | string or null | no | ISO date of the model run. |
| `temperature` | number or null | no | Sampling temperature when known. |
| `reasoning_effort` | string or null | no | Reasoning-effort setting when applicable. |
| `run_settings` | object | no | Provider-specific run settings. |
| `metadata_source` | string or null | no | `api` or `self_report` — how model/version/date were obtained. |

#### `source.artifacts[]`

| Field | Type | Description |
|---|---:|---|
| `kind` | string | `raw_response`, `api_response`, `screenshot`, or `prompt`. |
| `path` | string | Repository-relative path to the stored file. |
| `sha256` | string | Lowercase hex SHA-256 of the file's bytes; verified on load. |
| `media_type` | string or null | Optional MIME type. |

### Provenance coherence rules

The loader enforces, and reports violations as `P-01`:

- `synthetic` cases: `provenance_tier` `synthetic`, `source.kind` `synthetic`,
  `source.model_name` null.
- `reference_correct` cases: `provenance_tier` `deprecated`, `source.kind`
  `reviewer_synthesis`.
- `complete` `real_world` cases: `provenance_tier` `gold` or `silver`,
  `raw_output_available` true, and at least one `raw_response` or `api_response`
  artifact whose file exists and matches its hash.

### `llm_response`

| Field | Type | Description |
|---|---:|---|
| `prompt` | string | Prompt text or pointer to the canonical prompt file. |
| `response` | string | Raw LLM response, or empty string for pending captures. |

### `expected_result`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `value` | number or null | Expected final numerical value, if scalar. |
| `unit` | string or null | Expected final unit. |
| `method` | string | Trusted calculation method. |
| `required_assumptions` | array | Assumptions required for the method. |

### `outputs`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `name` | string | Stable output identifier, such as `hoop_stress`. |
| `symbol` | string | Engineering symbol used by the response. |
| `value` | number | Reported numerical value. |
| `unit` | string or null | Reported unit. |
| `source` | string | `llm` or `expected`. |
| `convention` | string or null | Optional convention tag for convention-sensitive values. |

For pressure-vessel hoop and longitudinal stresses, multiple values for the same
quantity are allowed when they represent explicit conventions such as
`inner_radius` and `mean_radius`. The convention should be represented by the
`convention` field rather than only by a name suffix.

### `tolerance`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `relative` | number or null | Relative tolerance as a fraction. Default is `0.005`. |
| `absolute` | number or null | Absolute tolerance in output units when needed. |
| `policy` | string | Link or short name for the tolerance policy used. |
| `accepted_conventions` | array or null | Optional convention names accepted for convention-sensitive recomputations. Defaults to `["inner_radius"]` when omitted. |

Supported pressure-vessel hoop-stress conventions are `inner_radius`,
`mean_radius`, and the quarantined `effective_radius_0p6t` heuristic.
Non-default conventions must be justified in `notes.reviewer_notes`.
`accepted_conventions` is optional and defaults to `["inner_radius"]`.

### Model self-review and self-grades

Model self-reviews, self-scores, and self-selected material properties are not
represented as structured fields. They are evidence, not verifier ground truth,
and belong in the stored raw artifact and `llm_response.response`, not in
`expected_result`. The verifier never ingests a model's self-grade.

### `formulas_used`

Each formula record should include `formula_id` so the first verifier can use
canonical formula identities instead of brittle string parsing. Initial formula
IDs include `hoop_stress_thin_wall`, `longitudinal_stress_thin_wall`,
`yield_safety_factor`, and `axial_stress`.

## Valid Example

```json
{
  "case_id": "syn-fm07-0001",
  "schema_version": "0.3.0",
  "source_type": "synthetic",
  "status": "complete",
  "source": {
    "kind": "synthetic",
    "description": "Synthetic case for reasoning consistency.",
    "provenance_tier": "synthetic",
    "raw_output_available": true,
    "model_name": null,
    "model_version": null,
    "run_date": null,
    "temperature": null,
    "run_settings": {}
  },
  "prompt_id": "synthetic_pressure_vessel_fm07",
  "problem_statement": "Find hoop stress for a thin-walled cylindrical pressure vessel with p = 1.2 MPa, r = 50 mm, and t = 3 mm.",
  "llm_response": {
    "prompt": "Solve the pressure vessel problem and show your work.",
    "response": "sigma_h = p r / t. Substituting gives 25 MPa. Therefore the hoop stress is 20 MPa."
  },
  "expected_result": {
    "value": 20,
    "unit": "MPa",
    "method": "sigma_h = p r / t",
    "required_assumptions": ["thin-walled cylinder", "internal pressure", "hoop stress requested"]
  },
  "failure_modes": ["FM-07"],
  "formulas_used": [
    {
      "id": "eq1",
      "formula_id": "hoop_stress_thin_wall",
      "equation": "sigma_h = p * r / t",
      "purpose": "Compute hoop stress",
      "variables": {
        "sigma_h": "hoop_stress",
        "p": "pressure",
        "r": "radius",
        "t": "wall_thickness"
      }
    }
  ],
  "inputs": {
    "pressure": {"value": 1.2, "unit": "MPa"},
    "radius": {"value": 50, "unit": "mm"},
    "thickness": {"value": 3, "unit": "mm"},
    "yield_strength": {"value": 120, "unit": "MPa"}
  },
  "outputs": [
    {"name": "hoop_stress_substitution", "symbol": "sigma_h", "value": 25, "unit": "MPa", "source": "llm", "convention": "inner_radius"},
    {"name": "hoop_stress_final", "symbol": "sigma_h", "value": 20, "unit": "MPa", "source": "llm", "convention": "inner_radius"},
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 20, "unit": "MPa", "source": "expected", "convention": "inner_radius"}
  ],
  "units": {
    "system": "SI",
    "canonical_outputs": {
      "stress": "MPa"
    }
  },
  "tolerance": {
    "relative": 0.005,
    "absolute": null,
    "policy": "docs/tolerance_policy.md",
    "accepted_conventions": ["inner_radius"]
  },
  "notes": {
    "assumptions_stated": ["thin-walled cylinder"],
    "limitations": ["Synthetic example, not a transcript-backed real run."],
    "reviewer_notes": "Final answer is correct, but the substitution line is inconsistent.",
    "expected_verifier_behavior": "Flag FM-07 because recomputation yields 20 MPa while the stated substitution says 25 MPa."
  }
}
```

## Invalid Example

```json
{
  "case_id": "rw-0001",
  "source_type": "real_world",
  "problem_statement": "Calculate stress.",
  "answer": "It is fine."
}
```

This is invalid because it omits required metadata, model/run fields,
`llm_response`, `expected_result`, `failure_modes`, `formulas_used`, `inputs`,
`outputs`, `units`, `tolerance`, and `notes`.

## Parsing Failure Category

Malformed benchmark data should be reported as `P-01: Schema Noncompliance`.
Future verifier behavior is to emit a diagnostic report and skip engineering
checks when the metadata block is missing or invalid.
