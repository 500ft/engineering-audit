# MechAudit

MechAudit is a benchmark-driven project for verifying LLM-generated mechanical
engineering calculations. The first version focuses on failures that are common
when language models solve statics, mechanics of materials, machine design, and
pressure-vessel-style problems: calculation mistakes, unit inconsistencies,
incorrect formulas, missing assumptions, and reasoning that does not match the
final answer.

The project is intentionally benchmark-led: benchmark cases define the behavior
the verifier must catch, and the verifier is kept narrow enough that its checks
remain independently recomputable.

## Current Scope

- Audit the initial pressure-vessel and axial-stress benchmark cases.
- Detect documented synthetic failure modes without echoing metadata labels.
- Treat completed real pressure-vessel captures as false-positive controls when
  the model output is correct.
- Keep broad engineering-domain coverage, raw-response extraction, and
  code-specific compliance checks out of scope for v1.

## Real-Capture Status

The repository does **not** yet contain a verbatim model capture. Provenance is
enforced by the loader as of schema `0.3.0`; see `docs/capture_provenance.md`.

- Reviewer-synthesized controls (not real captures): Gemini 3.5 Thinking
  (`gemini-0001`), Claude Opus 4.8 High plain solve (`claude-0001`), and Claude
  Opus 4.8 High design-review prompt (`claude-0002`). These are `source_type:
  reference_correct`, `provenance_tier: deprecated`. They were written by a
  reviewer to describe a model run, carry no raw transcript, and are retained
  only as no-failure false-positive controls — most usefully the `20.0 MPa`
  inner-radius result versus the defensible `20.6 MPa` mean-radius refinement.
- Pending real captures: `gpt-0001` and `gpt-0002` (`status: pending_capture`).

Genuine `gold`/`silver` captures with verbatim raw artifacts are the next
milestone; the loader rejects any `complete` `real_world` case that lacks a
hash-verified artifact.

## Repository Layout

```text
docs/
  failure_taxonomy.md   Failure modes the verifier should eventually detect.
  schema_contract.md    Structured output contract (schema 0.3.0) for benchmark data.
  capture_provenance.md Provenance tiers and raw-artifact rules.
  tolerance_policy.md   Numeric comparison defaults for benchmark checks.
prompts/
  pressure_vessel_prompt_v1.md  Canonical prompt for real-run benchmark capture.
benchmark/
  README.md             Benchmark case format and contribution rules.
  real_world/           Transcript-backed cases from real model runs.
  real_world/raw/       Verbatim raw artifacts referenced by complete cases.
  synthetic/            Clearly labeled artificial cases for targeted coverage.
```

## V1 Exit Criteria

V1 is complete when the verifier can process the benchmark schema, generate a
Markdown audit report for each case, catch the documented failures in the initial
benchmark set, avoid false positives on correct cases, and pass the project test
suite.
