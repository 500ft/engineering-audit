# Contributing

engineering-audit is benchmark-driven: observed or deliberately constructed
cases define the behavior before verifier logic is extended.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
```

## Checks

```bash
pytest
engineering-audit eval benchmark/
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

Use `engineering-audit capture` so prompt, response, metadata, and digests are
stored together. Do not edit a completed raw artifact in place. Create a new run
when the prompt, response, model settings, or metadata change.

## CAD loop

`cadloop/` needs a Windows host with SOLIDWORKS licensed, so only its oracle
tests run in CI. When changing it:

1. State which stage of [`docs/cad_fea_loop.md`](docs/cad_fea_loop.md) the change
   affects.
2. Keep the acceptance gate honest. A build is accepted only when measured mass
   properties match a declared oracle; a job without an oracle reports
   `"accepted": null`, never a pass.
3. Do not commit host configuration. Credentials live outside the repository;
   `cadloop/config.example.json` documents the shape with placeholders.
4. Do not commit retrieved run artifacts except as deliberate evidence. STEP
   files, previews, and per-job directories under `cadloop/runs/` are ignored.
5. Record newly observed host API behaviour in
   [`docs/solidworks_api_findings.md`](docs/solidworks_api_findings.md) rather
   than only working around it in code.

## Pull requests

List the cases added or changed, the failure modes affected, and the output of
both the test suite and `engineering-audit eval benchmark/`.
