# cadloop

Parametric CAD builds on a SOLIDWORKS host, gated on a closed-form volume
oracle, exporting STEP for downstream FEA.

The loop this serves is documented in
[`../docs/cad_fea_loop.md`](../docs/cad_fea_loop.md). Host API behaviour that
the code works around is recorded in
[`../docs/solidworks_api_findings.md`](../docs/solidworks_api_findings.md).

## Layout

```text
orchestrator.py           workstation side: upload, launch, poll, retrieve
worker.py                 host side: one job, job.json in and result.json out
volume.py                 closed-form oracles and the acceptance comparison
author_template.py        host side: create the parametric fixture
inspect_template.py       host side: read a template's equation contract
measure_open_latency.py   host side: separate a slow open from a dead process
remote_run.py             run one host-side script that is not a job
jobs/                     job specifications
templates/                template contracts
runs/                     retrieved results and artifacts (not committed)
```

## Host requirements

- Windows with SOLIDWORKS licensed and installed, OpenSSH Server enabled.
- Python 3.12 with `pywin32`, and `PsExec` available at the configured path.
- A logged-in interactive session. SOLIDWORKS' COM server will not start from a
  non-interactive SSH session, so the worker is launched into that session by
  session id; the session must exist and the configured account must own it.

## Configuration

Copy `config.example.json` to a location outside the repository and point
`CADLOOP_HOST_CONFIG` at it. The default is
`~/.config/sw_pc_credentials.json`. It holds a Windows account password in
plaintext, so it belongs outside version control with owner-only permissions.
`PsExec` passes that password as a process argument on the host, which is
visible to anything that can read the host's process list; this is a property
of the launch mechanism, not of where the file is stored.

## Use

Author the fixture once per host:

```bash
python cadloop/remote_run.py cadloop/author_template.py template_build_result.json
```

Confirm what the saved template declares:

```bash
python cadloop/remote_run.py cadloop/inspect_template.py template_contract.json
```

Run a job:

```bash
python cadloop/orchestrator.py cadloop/jobs/plate-150x80x6.json
```

`orchestrator.py` exits nonzero unless the worker accepted the build and every
declared artifact arrived on local disk. Results land in `cadloop/runs/<job_id>/`.

## Acceptance

A clean rebuild is not evidence that the requested geometry exists. Each job
names an oracle; the worker compares measured mass properties against it and
fails the job on disagreement. A job that names no oracle records
`"accepted": null` and is reported as unverified rather than as a pass.

Oracle arithmetic is tested in `tests/test_cad_volume_oracle.py`, which runs in
CI without SOLIDWORKS. Nothing else here runs in CI: the rest needs the host.
