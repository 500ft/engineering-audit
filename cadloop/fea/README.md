# cadloop/fea

Solves a cadloop CAD output on a licensed MAPDL instance and returns
displacement and stress measurements. This is the FEA stage described in
[`../../docs/cad_fea_loop.md`](../../docs/cad_fea_loop.md).

## Why this is separate from the CAD stage

The CAD stage runs a SOLIDWORKS worker inside an interactive Windows session
via PsExec, because SOLIDWORKS' COM server will not start otherwise. MAPDL has
no such requirement — it is a console application — so this stage launches it
directly over SSH and drives it from the workstation over gRPC. The two stages
share a host but not a launch mechanism.

## Why IGES, not STEP

`worker.py` exports both. MAPDL has no reliable direct STEP reader; the
documented, working import path is IGES through `AUX15`/`IGESIN`. IGES is
exported from the same open SOLIDWORKS document as the STEP file, so both
represent the same geometry — the IGES file is not a converted, secondary copy.

IGES import produces surfaces, not a volume: 8 areas and 0 volumes for the
plate fixture. `inspect_geometry.py` reports this rather than assuming it, and
`run_static_plate.py` builds the volume explicitly with `VA` before meshing.

## Host requirements

- The MAPDL executable, already required for `ANSYS Student` licensing
  elsewhere on the host: `C:\Program Files\ANSYS Inc\ANSYS Student\<version>\ansys\bin\winx64\ANSYS<version>.exe`.
- SSH access, as for the CAD stage. No PsExec, no interactive session.

## Configuration

Uses the same `CADLOOP_HOST_CONFIG` file as the CAD stage (`ssh_host`,
`ssh_user`, `ssh_key`).

## Use

Launch MAPDL in gRPC mode on the host. It binds `127.0.0.1` only — a gRPC
server argument, not a firewall setting — so it is unreachable from the
workstation without a tunnel:

```bash
ssh -i <key> <user>@<host> \
  'cd /d C:\CADLoop\fea_run && "<ansys_exe>" -grpc -smp -np 2 -port 50052 -j feajob'
```

`-smp` matters: the same executable in its default distributed-memory mode
started an `ANSYS<version>.exe` wrapper process that stayed at a few
kilobytes of memory and never bound the port. `-smp` is what produced the real
solver process and a listening socket in the run this stage was verified
against.

In a second terminal, tunnel the port and hold the tunnel open for the
workstation session:

```bash
ssh -i <key> -L 50052:127.0.0.1:50052 -N <user>@<host>
```

Install the workstation client once: `pip install -e ".[fea]"` from the
repository root.

Then, from the workstation:

```bash
python cadloop/fea/inspect_geometry.py cadloop/runs/<job_id>/<job_id>.igs \
  --result cadloop/runs/<job_id>/geometry_inspection.json

python cadloop/fea/run_static_plate.py <Length_mm> <pressure_MPa> \
  --result cadloop/runs/<job_id>/static_plate_result.json
```

`inspect_geometry.py` must run first: it imports the IGES file and merges
coincident entities into the session `run_static_plate.py` then builds a
volume from. Both scripts connect to an already-running MAPDL session and
never call `mapdl.exit()`, because neither owns the process it connects to.
Exit the session yourself when done, or let the host-side process outlive the
scripts.

## What this does not yet do

- **One fixture, one load case.** `run_static_plate.py` is written for the
  plate-with-center-hole template: it fixes the face at `X=0` and pressurizes
  the face at `X=Length`, both assumptions read from
  `docs/cad_fea_loop.md`'s bounding-box convention, not derived generally. A
  different template needs different boundary conditions, not a parameter.
- **No FEA-side oracle.** The CAD stage gates on a closed-form volume. This
  stage reports displacement and stress with no independent check that they
  are correct — only that the solve completed and the values are finite.
  Comparing against a closed-form plate-with-hole stress-concentration result
  is the natural next gate and is not implemented.
- **Not orchestrated.** `inspect_geometry.py` and `run_static_plate.py` are
  run by hand against a manually launched MAPDL session. There is no
  `orchestrator.py`-equivalent that launches MAPDL, tunnels it, runs both
  scripts, and retrieves a single `result.json`.
