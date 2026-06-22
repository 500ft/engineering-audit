# Real-World Benchmark Case Template

Use this template only for transcript-backed cases from actual engineering work.
Do not claim a case is real-world unless the prompt, LLM response, and trusted
correction are available.

## Metadata

- Case ID:
- Schema version: `0.3.0`
- Source type: `real_world`
- Status: `pending_capture` or `complete`
- Provenance tier: `gold` (API) or `silver` (UI transcript). See
  `docs/capture_provenance.md`.
- Course or project context:
- Date of LLM interaction:
- Model name / version:
- Prompt ID:
- Temperature / run settings:
- Anonymization notes:

A `complete` real_world case must store the verbatim model output under
`benchmark/real_world/raw/` and reference it from `source.artifacts` with a
matching SHA-256, or the loader rejects it as `P-01`. Compute a hash with
`shasum -a 256 <file>`.

```json
{
  "case_id": "",
  "schema_version": "0.3.0",
  "source_type": "real_world",
  "status": "pending_capture",
  "source": {
    "kind": "manual_model_run",
    "description": "",
    "provenance_tier": null,
    "raw_output_available": false,
    "capture_protocol": "standard",
    "artifacts": [],
    "provider": null,
    "model_name": null,
    "model_version": null,
    "run_date": null,
    "temperature": null,
    "run_settings": {},
    "metadata_source": null
  },
  "prompt_id": "pressure_vessel_prompt_v1",
  "problem_statement": "",
  "llm_response": {
    "prompt": "prompts/pressure_vessel_prompt_v1.md",
    "response": ""
  },
  "expected_result": {
    "value": null,
    "unit": null,
    "method": "",
    "required_assumptions": []
  },
  "failure_modes": [],
  "formulas_used": [],
  "inputs": [],
  "outputs": [],
  "units": {
    "system": "SI",
    "canonical_outputs": {}
  },
  "tolerance": {
    "relative": 0.005,
    "absolute": null,
    "policy": "docs/tolerance_policy.md"
  },
  "notes": {
    "assumptions_stated": [],
    "limitations": ["Pending raw model output."],
    "reviewer_notes": "",
    "expected_verifier_behavior": "Pending classification after raw output is captured."
  }
}
```

When the case is `complete`, set `status: "complete"`,
`source.provenance_tier` to `gold` or `silver`,
`source.raw_output_available: true`, and add at least one artifact, e.g.:

```json
"artifacts": [
  {"kind": "raw_response", "path": "benchmark/real_world/raw/<case_id>.txt", "sha256": "<hex>", "media_type": "text/plain"},
  {"kind": "screenshot", "path": "benchmark/real_world/raw/<case_id>.png", "sha256": "<hex>", "media_type": "image/png"}
]
```

## Original Engineering Problem

```text
Paste the original problem statement here.
```

## LLM Prompt

```text
Paste the exact prompt sent to the LLM here.
```

## LLM Response

```text
Paste the exact LLM response here.
```

## Trusted Expected Result

```text
Show the trusted solution, reference answer, or manually verified result here.
```

## Classified Failure Modes

- `FM-XX`:

## Expected Future Verifier Behavior

Describe what the verifier should flag, what it should ignore, and what report
message would make the issue clear to a human reviewer.

## Inputs

| Name | Symbol | Value | Unit |
|---|---:|---:|---|
|  |  |  |  |

## Outputs

| Name | Symbol | Value | Unit | Source |
|---|---:|---:|---|---|
|  |  |  |  |  |

## Notes

- Assumptions stated by LLM:
- Assumptions required by trusted method:
- Limitations:
- Reviewer notes:
