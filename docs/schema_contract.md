# Schema Contract

This document defines the structured data contract future MechAudit verifier
code should consume. It is a documentation contract only; no validator is
implemented in this phase.

## Version

Current draft schema version: `0.2.0`

Schema versions use semantic versioning:

- Patch changes clarify wording or examples without changing fields.
- Minor changes add optional fields.
- Major changes rename fields, remove fields, or change required semantics.

## Benchmark File Format

Benchmark cases are Markdown files with a fenced `json` metadata block near the
top. The Markdown makes cases readable in GitHub; the JSON block gives the
future verifier a stable parse target.

## Required Top-Level Fields

| Field | Type | Required | Description |
|---|---:|---:|---|
| `case_id` | string | yes | Stable benchmark identifier. |
| `schema_version` | string | yes | Schema version used by this case. |
| `source_type` | string | yes | One of `synthetic`, `real_world`, or `reference_correct`. |
| `status` | string | yes | One of `complete`, `pending_capture`, or `needs_review`. |
| `source` | object | yes | Provenance and capture source. |
| `model_name` | string or null | yes | Model product name, or `null` for synthetic cases. |
| `model_version` | string or null | yes | Model version or release identifier when known. |
| `run_date` | string or null | yes | ISO date when the model run was captured. |
| `prompt_id` | string | yes | Stable prompt identifier. |
| `temperature` | number or null | yes | Sampling temperature when known. |
| `run_settings` | object | yes | Provider-specific run settings. |
| `problem_statement` | string | yes | Original engineering problem. |
| `llm_response` | object | yes | Prompt and raw model response being audited. |
| `expected_result` | object | yes | Trusted answer or trusted method. |
| `failure_modes` | array | yes | Expected labels from the taxonomy. |
| `formulas_used` | array | yes | Formula records stated by the LLM or expected solution. |
| `inputs` | object or array | yes | Named numerical inputs with units. Completed synthetic cases use object form. |
| `outputs` | array | yes | Named numerical outputs with units. |
| `units` | object | yes | Unit system and canonical units. |
| `tolerance` | object | yes | Numeric tolerance policy for the case. |
| `notes` | object | yes | Assumptions, limitations, and reviewer notes. |

## Field Details

### `source`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `kind` | string | `synthetic`, `manual_model_run`, `api_model_run`, or `coursework_transcript`. |
| `description` | string | Human-readable provenance. |
| `raw_output_available` | boolean | Whether raw LLM output is present in the file. |

### `llm_response`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `prompt` | string | Prompt text or pointer to the canonical prompt file. |
| `response` | string | Raw LLM response, or empty string for pending captures. |

Legacy `llm_response.model` and `llm_response.date` are replaced by
top-level `model_name`, `model_version`, and `run_date`.

### `expected_result`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `value` | number or null | Expected final numerical value, if scalar. |
| `unit` | string or null | Expected final unit. |
| `method` | string | Trusted calculation method. |
| `required_assumptions` | array | Assumptions required for the method. |

### `tolerance`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `relative` | number or null | Relative tolerance as a fraction. Default is `0.005`. |
| `absolute` | number or null | Absolute tolerance in output units when needed. |
| `policy` | string | Link or short name for the tolerance policy used. |

### `formulas_used`

Each formula record should include `formula_id` so the first verifier can use
canonical formula identities instead of brittle string parsing. Initial formula
IDs include `hoop_stress_thin_wall`, `longitudinal_stress_thin_wall`,
`yield_safety_factor`, and `axial_stress`.

## Valid Example

```json
{
  "case_id": "syn-fm07-0001",
  "schema_version": "0.2.0",
  "source_type": "synthetic",
  "status": "complete",
  "source": {
    "kind": "synthetic",
    "description": "Synthetic case for reasoning consistency.",
    "raw_output_available": true
  },
  "model_name": null,
  "model_version": null,
  "run_date": null,
  "prompt_id": "synthetic_pressure_vessel_fm07",
  "temperature": null,
  "run_settings": {},
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
    {"name": "hoop_stress_substitution", "symbol": "sigma_h", "value": 25, "unit": "MPa", "source": "llm"},
    {"name": "hoop_stress_final", "symbol": "sigma_h", "value": 20, "unit": "MPa", "source": "llm"},
    {"name": "hoop_stress", "symbol": "sigma_h", "value": 20, "unit": "MPa", "source": "expected"}
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
    "policy": "docs/tolerance_policy.md"
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
