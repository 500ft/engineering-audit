# Benchmark Cases

The benchmark defines what MechAudit should eventually verify. Cases should be
added before verifier logic whenever possible so implementation follows observed
failure behavior instead of imagined behavior.

## Folders

- `real_world/`: transcript-backed LLM failures from actual engineering work.
- `synthetic/`: clearly labeled artificial cases for targeted coverage. This
  includes both single-mode failure cases (`syn-fm*`, `syn-arith-*`) and
  analytically/FEA-grade-validated **ground-truth controls** (`syn-kt-hole-*`,
  `syn-cantilever-*`) whose correct answer is computed independently in-repo by
  `mechaudit.stress_concentration` and asserted in
  `tests/test_ground_truth_references.py`. The ground-truth controls are
  no-failure positives (`failure_modes: []`), `provenance_tier: synthetic`; they
  are not model runs and must never be described as wild captures.

Real-run capture slots may live in `real_world/` with `status:
pending_capture`, but they must not be described as completed real LLM failures
until the raw model output is present. Anonymize coursework, names, dates, or
project details when needed, but do not fabricate provenance.

Current pressure-vessel real-run status:

- Complete no-failure controls: `rw-pressure-vessel-gemini-0001`,
  `rw-pressure-vessel-claude-0001`, and `rw-pressure-vessel-claude-0002`.
- Pending captures: `rw-pressure-vessel-gpt-0001` and
  `rw-pressure-vessel-gpt-0002`.

The completed controls are populated from reviewer-provided capture synthesis
because the raw transcripts are not present in the repository. Their metadata
must keep that limitation explicit.

## Case Format

Each benchmark case is a Markdown file with a fenced `json` metadata block near
the top. The JSON block follows `docs/schema_contract.md`; the surrounding
Markdown explains the case for human reviewers.

## Case Requirements

Each benchmark case should include:

- Original engineering problem.
- LLM prompt.
- LLM response.
- Correct solution or trusted expected result.
- Classified failure mode labels from `docs/failure_taxonomy.md`.
- Expected future verifier behavior.
- Notes on assumptions, units, and limitations.
- Tolerance policy reference.

## Naming

Use stable lowercase identifiers:

- `rw-pressure-vessel-gpt-0001.md`
- `syn-fm01-0001.md`
- `syn-fm07-0001.md`

## Minimum Review Checklist

- The source is clearly labeled as real-world, synthetic, or reference-correct.
- Units are explicit for all numerical values.
- The expected result is traceable to a trusted calculation.
- The failure mode is documented in the taxonomy.
- The expected verifier behavior is stated in plain language.
- Correct real captures with `failure_modes: []` remain useful: they protect
  against false positives such as treating accepted radius conventions as
  arithmetic errors.
