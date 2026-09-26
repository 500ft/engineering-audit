# cadloop/fea

Takes a part the CAD stage built and exported, solves it on the licensed MAPDL
on the host, renders contour images, and checks the answer against a closed-form
result. One command:

```bash
.venv/bin/python cadloop/fea/run_fea.py
```

That launches MAPDL on the host, tunnels its gRPC port, imports the IGES, builds
the volume, meshes at several element sizes, solves, writes PNGs, and gates the
peak stress. Everything lands in `cadloop/fea/runs/`.

## Why there is an oracle and not just pictures

A contour plot is the weakest evidence this pipeline produces. A solve that ran
with the wrong boundary conditions, the wrong units, or a mesh too coarse to
resolve the feature produces a plausible, colourful, wrong image every time — and
it looks exactly like a right one.

This is not hypothetical here. The first version of this gate **rejected a correct
solve at 22% error**, because the Heywood/Howland stress-concentration series was
taken as gross-section referenced when it is net-section referenced; the
prediction was low by `W/(W-d)`, 32% for this plate. The images before and after
that fix are identical. Only the number moved.

So the run produces both, and the acceptance is the number:

- peak stress at the hole vs. Heywood/Howland for a finite-width plate,
- within 12% relative,
- on a model whose bounding box has been **measured** to match the geometry file.

## What the last run measured

`mounting_plate`, 80x50x8 mm with a 12 mm central hole, one end face fixed, 1 MPa
tension on the other, steel (E = 200 GPa, nu = 0.3).

| element size | elements | nodes | peak at hole |
| --- | --- | --- | --- |
| 5 mm | 1 769 | 3 409 | 2.811 MPa |
| 3 mm | 10 070 | 16 207 | 2.984 MPa |
| 2 mm | 25 291 | 39 475 | 2.973 MPa |

```
d/W 0.240   Kt(net) 2.4385   net/gross 1.3158
expected 3.2085 MPa   measured 2.9734 MPa   error 7.3%   agrees
bbox [80.0, 50.0, 8.0] at origin [0, 0, 0]
```

The images corroborate the number independently: peak at the hole edge
*perpendicular* to the load, minimum at the poles 90° away, far field at the
applied 1 MPa. That is Kirsch's four-lobe pattern, with the hole edge in
compression along the load axis. A wrong load direction or a unit error cannot
produce it.

## How good the agreement is, honestly

7.3% is agreement, not validation. The bias is **one-sided**: this plate and an
earlier 150x80x6 one both land *below* the correlation, by 7.3% and 9.1%. That is
the direction the model's own assumptions force — the correlation assumes a long
plate in uniform far-field tension with free lateral edges, while this model
clamps one end face completely and is only 1.6 widths long. Peak stress at a
raiser also converges from below as the mesh refines.

A tighter comparison would need a restraint that does not fight Poisson
contraction. That is the obvious next step and it is not done.

## Host notes

MAPDL v261 at
`C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe`.
Traps are catalogued in `docs/solidworks_api_findings.md` under *MAPDL / ANSYS on
this host*; the ones that cost the most time:

- A stale `<jobname>.lock` stops MAPDL starting **and it exits before opening a
  log** — no process, no port, no new file, nothing to read. `run_fea.py` deletes
  the lock before launching.
- `start /b` over SSH did not keep the server alive. It is launched over an SSH
  channel held open for the life of the run, and readiness is the listening port.
- `-smp` is required; the default distributed mode left a wrapper that never
  bound the port.
- Images need `pip install "ansys-mapdl-core[graphics]"`. Rendering is
  client-side, so nothing is installed on the host for it.
- ANSYS Student stops at 128k nodes. That is a licence ceiling: a sweep that hits
  it has run out of licence, not converged.

## Configuration

Same `CADLOOP_HOST_CONFIG` file as the CAD stage (`ssh_host`, `ssh_user`,
`ssh_key`). It holds a password, so it lives outside version control. See
`docs/host_setup.md`.

## What this does not yet do

- **One fixture, one load case.** The boundary conditions are written for a
  plate loaded along X. `run_fea.py` now refuses a part whose bounding box does
  not match the geometry file rather than silently solving a rotated model, but
  a different part still needs different boundary conditions, not a parameter.
- **No modal or nonlinear analysis.** Linear static only.
- **The restraint is cruder than the correlation assumes**, which is most of the
  7.3%. See above.
- **Not gated in CI.** `tests/test_fea_oracle.py` checks the closed-form
  prediction, which is what the gate rests on. The solve itself needs the host
  and a licence, so CI cannot run it.

## The older scripts

`inspect_geometry.py` and `run_static_plate.py` are the earlier two-step manual
route, kept because the 150x80x6 measurement above came from them. `run_fea.py`
supersedes both.
