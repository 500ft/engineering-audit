# Schema Contract

This document defines the structured data contract future MechAudit verifier
code should consume. It is a documentation contract only; no validator is
implemented in this phase.

## Version

Current draft schema version: `0.1.0`

Schema versions should use semantic versioning:

- Patch changes clarify wording or add examples without changing fields.
- Minor changes add optional fields.
- Major changes rename fields, remove fields, or change required semantics.

## Required Top-Level Fields

| Field | Type | Required | Description |
|---|---:|---:|---|
| `case_id` | string | yes | Stable benchmark identifier, such as `rw-0001` or `syn-fm07-0001`. |
| `schema_version` | string | yes | Schema version used by this case. |
| `source_type` | string | yes | One of `real_world`, `synthetic`, or `reference_correct`. |
| `problem_statement` | string | yes | Original engineering problem statement. |
| `llm_response` | object | yes | Prompt and response being audited. |
| `expected_result` | object | yes | Trusted answer or trusted method used for comparison. |
| `failure_modes` | array | yes | Expected failure labels, such as `FM-01`, `FM-02`, `FM-07`, or `P-01`. |
| `formulas_used` | array | yes | Formula records stated by the LLM or expected solution. |
| `inputs` | array | yes | Named numerical inputs with units. |
| `outputs` | array | yes | Named numerical outputs with units. |
| `units` | object | yes | Unit system and canonical units for the case. |
| `notes` | object | yes | Provenance, assumptions, limitations, and reviewer notes. |

## Field Details

### `case_id`

Use lowercase identifiers with a source prefix:

- `rw-0001` for real-world cases.
- `syn-fm07-0001` for synthetic targeted cases.
- `ref-0001` for correct reference cases.

### `source_type`

Allowed values:

- `real_world`: transcript-backed failure from actual engineering work.
- `synthetic`: artificial case designed to exercise a specific failure mode.
- `reference_correct`: correct case used to check false positives.

### `llm_response`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `model` | string | Model name if known. Use `unknown` if unavailable. |
| `date` | string | ISO date of the interaction if known. |
| `prompt` | string | Prompt sent to the LLM. |
| `response` | string | Raw LLM response. |

### `expected_result`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `value` | number or null | Expected final numerical value, if a single scalar is appropriate. |
| `unit` | string or null | Expected final unit. |
| `method` | string | Trusted calculation method. |
| `required_assumptions` | array | Assumptions required for the expected method. |
| `tolerance_relative` | number | Relative tolerance for numerical comparison. |

Use `null` for `value` and `unit` when the benchmark checks parsing or formula
selection rather than a single numerical result.

### `failure_modes`

The array must contain expected labels from `docs/failure_taxonomy.md`. Use an
empty array only for reference-correct cases.

### `formulas_used`

Each formula record requires:

| Field | Type | Description |
|---|---:|---|
| `id` | string | Stable identifier within the case, such as `eq1`. |
| `equation` | string | Parseable equation when possible. |
| `purpose` | string | What the formula is intended to compute. |
| `variables` | object | Mapping from symbols to input or output names. |

### `inputs`

Each input requires:

| Field | Type | Description |
|---|---:|---|
| `name` | string | Human-readable variable name. |
| `symbol` | string | Symbol used in formulas. |
| `value` | number | Numerical value. |
| `unit` | string | Unit exactly as used in the case. |

### `outputs`

Each output requires:

| Field | Type | Description |
|---|---:|---|
| `name` | string | Human-readable output name. |
| `symbol` | string | Symbol used in formulas. |
| `value` | number | Numerical value stated by the LLM or expected result. |
| `unit` | string | Output unit. |
| `source` | string | One of `llm`, `expected`, or `recomputed`. |

### `units`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `system` | string | Unit system, such as `SI`, `USCS`, or `mixed`. |
| `canonical_outputs` | object | Preferred output units by quantity. |

### `notes`

Required fields:

| Field | Type | Description |
|---|---:|---|
| `provenance` | string | Source of the benchmark case. |
| `assumptions_stated` | array | Assumptions explicitly stated by the LLM. |
| `limitations` | array | Known issues or scope limits for the case. |
| `reviewer_notes` | string | Human review notes. |

## Valid Example

```json
{
  "case_id": "syn-fm07-0001",
  "schema_version": "0.1.0",
  "source_type": "synthetic",
  "problem_statement": "Find hoop stress for a thin-walled cylindrical pressure vessel with p = 1.2 MPa, r = 50 mm, and t = 3 mm.",
  "llm_response": {
    "model": "synthetic",
    "date": "2026-05-29",
    "prompt": "Solve the pressure vessel problem and show your work.",
    "response": "sigma_h = p r / t. Substituting gives 25 MPa. Therefore the hoop stress is 20 MPa."
  },
  "expected_result": {
    "value": 20,
    "unit": "MPa",
    "method": "Trusted worked solution supplied by benchmark author.",
    "required_assumptions": ["thin-walled cylinder", "internal pressure", "hoop stress requested"],
    "tolerance_relative": 0.005
  },
  "failure_modes": ["FM-07"],
  "formulas_used": [
    {
      "id": "eq1",
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
  "inputs": [
    {"name": "pressure", "symbol": "p", "value": 1.2, "unit": "MPa"},
    {"name": "radius", "symbol": "r", "value": 50, "unit": "mm"},
    {"name": "wall_thickness", "symbol": "t", "value": 3, "unit": "mm"}
  ],
  "outputs": [
    {"name": "hoop_stress_substitution", "symbol": "sigma_h", "value": 25, "unit": "MPa", "source": "llm"},
    {"name": "hoop_stress_final", "symbol": "sigma_h", "value": 20, "unit": "MPa", "source": "llm"}
  ],
  "units": {
    "system": "SI",
    "canonical_outputs": {
      "stress": "MPa"
    }
  },
  "notes": {
    "provenance": "Synthetic example for schema documentation.",
    "assumptions_stated": ["thin-walled cylinder"],
    "limitations": ["Synthetic example for reasoning consistency, not a real-world transcript."],
    "reviewer_notes": "The final answer is correct, but the stated substitution says 25 MPa even though the formula and inputs recompute to 20 MPa."
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

This is invalid because it omits `schema_version`, `llm_response`,
`expected_result`, `failure_modes`, `formulas_used`, `inputs`, `outputs`,
`units`, and `notes`. It also uses `answer`, which is not a recognized
top-level field.

## Parsing Failure Category

Malformed LLM output should be reported as `P-01: Schema Noncompliance`.

Future verifier behavior:

1. Parse the response into this schema.
2. Validate required fields and types.
3. Emit a diagnostic report for missing or malformed fields.
4. Stop before engineering checks if the schema is invalid.
