# MechAudit

MechAudit is a benchmark-driven project for verifying LLM-generated mechanical
engineering calculations. The first version focuses on failures that are common
when language models solve statics, mechanics of materials, machine design, and
pressure-vessel-style problems: calculation mistakes, unit inconsistencies,
incorrect formulas, missing assumptions, and reasoning that does not match the
final answer.

The project is intentionally starting with documentation and benchmark cases
before verifier code. The benchmark defines the behavior the verifier must catch,
and the schema contract defines the structured output future tooling will
consume.

## Current Scope

- Define a failure taxonomy for mechanical engineering calculation audits.
- Build a benchmark set from real and synthetic LLM failures.
- Specify the structured schema future verifier code will require.
- Defer verifier implementation until the taxonomy and benchmark cases are
  concrete enough to test against.

## Repository Layout

```text
docs/
  failure_taxonomy.md   Failure modes the verifier should eventually detect.
  schema_contract.md    Structured output contract for benchmark and verifier data.
  tolerance_policy.md   Numeric comparison defaults for benchmark checks.
prompts/
  pressure_vessel_prompt_v1.md  Canonical prompt for real-run benchmark capture.
benchmark/
  README.md             Benchmark case format and contribution rules.
  real_world/           Transcript-backed failures from real engineering work.
  synthetic/            Clearly labeled artificial cases for targeted coverage.
```

## V1 Exit Criteria

V1 is complete when the verifier can process the benchmark schema, generate a
Markdown audit report for each case, catch the documented failures in the initial
benchmark set, avoid false positives on correct cases, and pass the project test
suite.
