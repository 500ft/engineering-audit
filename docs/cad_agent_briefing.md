# CAD and simulation: what this setup can do, and how to use it well

A briefing for a session picking up CAD or FEA work here. It covers what is
already built and proven, the one method that matters, and the specific mistakes
that cost build iterations so they are not repeated.

Read `docs/host_setup.md` if the host needs bringing up. Read
`docs/solidworks_api_findings.md` before writing any COM call.

## Where things live

Work spans two repositories. They do not overlap.

| | `500ft/engineering-audit` | `500ft/autonomous-racing-systems` |
| --- | --- | --- |
| Holds | the reusable CAD/FEA machinery | the RoboRacer mast deliverable |
| Paths | `cadloop/`, `cadloop/fea/` | `cad/solidworks/`, `cad/generate.py` |
| Contract | `cadloop/` gates on `volume.py` oracles | `cad/contract.json` (frozen specimen), `cad/solidworks/contract-assembly.v1.json` |
| CI | oracle tests only; authoring needs the host | same |

## What is proven to work

Each of these has a recorded run, not an intention.

**Author geometry natively in SOLIDWORKS over COM.** Three parts built from
scratch — tube, sleeve, split clamp with bore, slot and two cross-drilled bolt
holes across three sketch planes. Not STEP imports; real feature trees.

**Drive a saved part from named global variables.** Changing one variable
(`ClampEngagement` 35 → 40 mm) re-drove all three parts onto independently
computed new volumes at 1e-15 or better. Equations existing is *not* the test;
re-driving is.

**Verify geometry against an independent oracle.** CadQuery builds the same
geometry, SOLIDWORKS measures its own mass properties, the two are compared
before a part is reported built. Agreement is routinely 1e-16.

**Export and round-trip.** STEP exports re-imported into CadQuery match the
contract to ~1e-16.

**Run FEA on the result.** IGES → MAPDL over gRPC → volume built from imported
surfaces → `SOLID186` free tetrahedral mesh → linear static solve → displacement
and stress. A 150×80×6 mm plate at 1 MPa gave 0.000776 mm and 2.75 MPa, a ~2.75×
concentration on nominal, consistent with a circular hole in a finite plate.

## The method that matters

**A clean rebuild is not evidence.** SOLIDWORKS reporting no error does not mean
it produced the geometry you asked for. This is not a theoretical concern — it
happened three separate times in one week:

1. A job reported `status: ok` while returning the *template's original* volume.
   The parameters had been written but never reached a dimension.
2. Equation links were silently rejected. The template read back its global
   variables, looked parametric, and drove nothing.
3. Three `FeatureCut4` calls returned `None`. Nothing raised. The result was a
   solid block with no bore, no slot and no holes — and a `.sldprt`, a `.step`
   and a preview image that all looked plausible.

In every case a screenshot would have passed. The number did not.

So: **every part gets a closed-form or independently-computed expected value, and
is refused if it disagrees.** `cadloop/volume.py` holds the oracles for the plate
fixture; `cad/solidworks/oracle.py` builds arbitrary geometry in CadQuery for the
mast assembly. A job that declares no oracle records `"accepted": null` and is
reported unverified, never as a pass.

The oracle also finds design errors, not just modelling ones. A slot placed
exactly tangent to the clamp bore showed up as a 2.579 mm³ discrepancy. The
modelling cause was SOLIDWORKS perturbing a tangent sketch edge; the design cause
was that a tangent slot leaves a knife edge and cannot close on the tube. One
number, two bugs.

## Rules that save iterations

**Look up API signatures; do not recall them.** Recalled signatures were wrong
repeatedly — `FeatureCut4` takes 27 positional arguments, `FeatureExtrusion3`
takes 23, and the enum values are not guessable. A web search for the method name
plus "VBA example" resolves it in one step. This single habit removed more
iterations than anything else.

**Measure orientation, do not assume it.** Sketch axis mapping on a datum plane
is not documented in any obvious place and is not intuitive. On this host a Right
Plane sketch at local `(x, y)` lands at global `(Y=y, Z=-x)`. That was determined
by `cad/solidworks/probe_right_plane.py`: draw one known circle, extrude it, read
the bounding box. A probe run costs one minute; guessing cost an iteration.
The same applies to the MAPDL side — `cadloop/fea/inspect_geometry.py` reports an
imported model's real bounding box before any boundary condition is written.

**Check return values.** SOLIDWORKS returns status codes that look like success.
`Add2` returns `-1` for a rejected equation and keeps going. `SaveAs3` returned
both `0` and `1` for saves that produced valid files, so it cannot be truth-tested
in either direction — check that the file exists and is non-empty instead. One
rejected equation invalidates every later one in the batch, so check each index.

**Instrument before iterating.** Each SOLIDWORKS run costs 90–120 seconds. Record
the volume after every feature rather than only at the end; a per-feature trace
localises a failure in one run instead of three. When two candidate fixes exist
(a direction flag, say), try both inside the same run and record which worked.

**Build one closed contour per feature.** A sketch holding two concentric circles
is rejected by `FeatureExtrusion3`. A tube is a cylinder plus a bore cut.

## How to run a CAD task

1. Put every dimension in one JSON with an evidence state per value. Both the
   oracle and the authoring script read it, so they cannot disagree.
2. Build the oracle first and sanity-check it by hand. An oracle that agrees with
   a wrong model to 1e-16 is still wrong; the mast oracle was confirmed against an
   independent hand calculation including the slot/bore intersection.
3. Author in SOLIDWORKS, measuring against the oracle before reporting success.
4. Prove it is parametric by re-driving a variable and measuring again.
5. Round-trip the STEP through CadQuery as a final independent check.

```bash
# engineering-audit
python cadloop/orchestrator.py cadloop/jobs/plate-150x80x6.json

# autonomous-racing-systems
~/ENTER/envs/rr-cad/bin/python cad/solidworks/oracle.py
python3 cad/solidworks/run_host.py cad/solidworks/author_mast_assembly.py authoring_result.json 900
python3 cad/solidworks/run_host.py cad/solidworks/redrive.py redrive_result.json 700
```

## Evidence discipline

`cad/roboracer/parameters.csv` is a register: every parameter carries an evidence
state and an acquisition route. The routes mean different things and a session
must respect the difference:

| Route | Who resolves it |
| --- | --- |
| `design_then_inspect` | the designer chooses, the built part is inspected later |
| `vendor_drawing` | a published drawing closes it |
| `measurement` | only measuring the physical part closes it |

A drawing cannot close a `measurement` parameter, however good the drawing is.
Changing that requires amending the acquisition route prospectively and in
writing.

**Do not invent a blocked value.** Model what is resolved, omit what is not, and
say which is which. Designer choices go in the geometry file tagged
`provisional_design` and do not get copied into the register without inspection.
The generator fails closed on a pending parameter by design; that refusal is
correct behaviour, not an obstacle.

## Known gaps

- **No assembly document and no mates.** Parts are built individually. There is
  no assembly STEP and therefore no assembly modal run. The assembly API is
  untested.
- **No drawing set.** Dimensioned drawings with tolerances have not been
  attempted through the API.
- **Positions are not fully parametric.** On the clamp, block size and bore
  diameter are driven by variables; slot and bolt-hole *positions* are authored
  coordinates, so large engagement changes would need repositioning.
- **No FEA-side oracle.** The CAD stage gates on volume. The FEA stage reports
  displacement and stress with no independent check that they are right, only
  that the solve completed. Comparing against a closed-form stress-concentration
  result is the natural next gate.
- **Host timing is unstable.** A single `OpenDoc6` has taken from seconds to
  13 minutes 18 seconds. Retry the open and poll for results on a long deadline;
  never infer completion from a launch call returning.
