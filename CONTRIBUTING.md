# Contributing

MechAudit is benchmark-driven: observed or deliberately constructed cases define
the behavior before verifier logic is extended.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
```

## Checks

```bash
pytest
mechaudit eval benchmark/
```

Both commands must pass. The batch evaluator is also a false-positive gate for
reference cases whose expected failure-mode set is empty.

## Adding a benchmark case

1. Start from the appropriate template under `benchmark/`.
2. Use a stable lowercase case identifier.
3. Include explicit units, assumptions, expected values, and tolerances.
4. Record expected failure modes using `docs/failure_taxonomy.md`.
5. Add or update tests before changing verifier logic.
6. Keep synthetic, reviewer-authored, and captured model outputs in their
   respective provenance tiers.

Do not describe a pending slot as a completed capture, and do not create a raw
model transcript from a summary.

## Captured outputs

Use `mechaudit capture` so prompt, response, metadata, and digests are stored
together. Do not edit a completed raw artifact in place. Create a new run when
the prompt, response, model settings, or metadata change.

## Pull requests

List the cases added or changed, the failure modes affected, and the output of
both the test suite and `mechaudit eval benchmark/`.
