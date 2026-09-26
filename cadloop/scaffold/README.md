# CAD scaffold: copy this to model a new part

A minimal, working, end-to-end part that another session can copy and adapt: one
plate with a centred through hole, authored natively in SOLIDWORKS over COM,
gated against an independent CadQuery oracle, and proven parametric by re-driving
its global variables. Every trap this host has produced is encoded in
`swhelpers.py` so you do not rediscover them.

Read `docs/cad_agent_briefing.md` first for the method, `docs/host_setup.md` to
bring the host up, and `docs/solidworks_api_findings.md` before changing any COM
call.

## Files

| File | Side | What it is |
| --- | --- | --- |
| `geometry.json` | shared | Every dimension, one `evidence_state` per value. Read by both the oracle and the authoring script so they cannot disagree. |
| `oracle.py` | workstation | Builds the same part in CadQuery and writes `oracle.json`: the baseline expectation plus one expectation per re-drive case. |
| `redrive.json` | shared | The parameter-change cases. Each names the global variable, the `geometry.json` path it corresponds to, and the new value — one declaration, so the oracle and the host cannot disagree about what changed. |
| `author_part.py` | host | Builds the part, saves it, reopens it, and decides acceptance. |
| `redrive.py` | host | `run_cases()`, called by `author_part.py`; also a standalone entry point for re-checking a part already built. |
| `swhelpers.py` | host | The trap-encoding library. Read its docstrings before working around anything. |
| `run_host.py` | workstation | Uploads, launches through PsExec into the interactive session, polls for the result, retrieves it. |
| `probe_*.py`, `toggle_probe.py` | host | The diagnostic kit. Probing costs one host run; guessing costs an iteration. |

## Running it

```bash
# workstation: build the expectation first, and sanity-check it by hand
.venv/bin/python cadloop/scaffold/oracle.py

# host: author, verify, re-drive
python cadloop/scaffold/run_host.py cadloop/scaffold/author_part.py author_result.json 900
```

A run takes roughly two to four minutes. `author_result.json` holds a per-stage
trace, the measured-against-oracle comparison and the re-drive outcome. The
committed `author_result.json` is the last accepted run, kept as evidence.

CI holds the workstation half: `tests/test_scaffold_oracle.py` checks that
`oracle.py` still reproduces `oracle.json` and that each re-drive case actually
changes the volume enough to detect an inert part.

## Adapting it to your part

1. Put your dimensions in `geometry.json`, one `evidence_state` per value. Do not
   invent a value whose evidence state says it must be measured or taken from a
   vendor drawing; leave it blocked and say so.
2. Build the same geometry in `oracle.py`. Check it by hand — an oracle that
   agrees with a wrong model to 1e-16 is still wrong.
3. Write re-drive cases in `redrive.json` that change the volume materially.
4. Replace `build_part()` in `author_part.py`. One closed contour per feature.
5. Name the global variables the register should own in the equations block.

## What acceptance means here

A part is accepted only when all of this holds, and `status` is `error`
otherwise:

- the **reopened saved file** rebuilds with no feature in error,
- it contains exactly one solid body,
- its measured volume matches the CadQuery oracle within 1e-6 relative,
- and **every re-drive case drives the geometry onto its own oracle value**.

The order matters. Acceptance is measured on the reopened file rather than the
session that authored it, because what ships is the file, and because the
`Equations` folder reports an error for the rest of the authoring session no
matter how many rebuilds are forced.

The re-drive is not a nicety. Building this scaffold, the oracle passed at 1e-16
on a part that was **not parametric**: `CreateCornerRectangle` had dimensioned its
own rectangle, so the dimensions added afterwards were a second pair on the same
edges and drove nothing. That is sticky host state rather than API behaviour — the
same call did not auto-dimension the RoboRacer clamp authored earlier on this host
— which is why `clear_sketch_dimensions` runs unconditionally instead of trying to
detect it. The part was drawn at the intended size, so it measured
exactly right. Changing `PlateLength` from 80 to 100 mm moved the bore and left
the plate at 80×50 — and that is the only reason the defect was found. A clean
rebuild, a correct volume, a plausible preview image and a valid STEP file were
all present the whole time.

So: the oracle catches wrong geometry, and the re-drive catches a model that is
right once and cannot be changed. Neither substitutes for the other.
