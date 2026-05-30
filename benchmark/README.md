# Benchmark Cases

The benchmark defines what MechAudit should eventually verify. Cases should be
added before verifier logic whenever possible so implementation follows observed
failure behavior instead of imagined behavior.

## Folders

- `real_world/`: transcript-backed LLM failures from actual engineering work.
- `synthetic/`: clearly labeled artificial cases for targeted coverage.

Do not place a case in `real_world/` unless the original prompt, LLM response,
and trusted correction are available. Anonymize coursework, names, dates, or
project details when needed, but do not fabricate provenance.

## Case Requirements

Each benchmark case should include:

- Original engineering problem.
- LLM prompt.
- LLM response.
- Correct solution or trusted expected result.
- Classified failure mode labels from `docs/failure_taxonomy.md`.
- Expected future verifier behavior.
- Notes on assumptions, units, and limitations.

## Naming

Use stable lowercase identifiers:

- `rw-0001.md`
- `syn-fm01-0001.md`
- `syn-fm07-0001.md`

## Minimum Review Checklist

- The source is clearly labeled as real-world, synthetic, or reference-correct.
- Units are explicit for all numerical values.
- The expected result is traceable to a trusted calculation.
- The failure mode is documented in the taxonomy.
- The expected verifier behavior is stated in plain language.
