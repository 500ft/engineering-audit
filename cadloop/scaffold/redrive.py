"""Prove the equations drive the model. Runs on the host, after the part is saved.

A part can hold equations that look right and that nothing listens to. It
measures correctly until a parameter changes -- and then it still measures
correctly, which is the failure. This is not hypothetical: on this host the
rectangle tool dimensions its own rectangle, so dimensions added afterwards
report driving while the tool's already fix the geometry. The oracle passes,
because the part was drawn at the intended size. Only a parameter change sees it.

Each case in redrive.json changes a global variable; the resulting volume is
checked against the CadQuery expectation oracle.py computed for that same change.
An inert-equation part returns the baseline volume instead, which is recorded so
a failure says which of the two happened.

author_part.py calls run_cases as part of acceptance. This file is also a
standalone entry point for re-checking a part that is already built:

    python redrive.py <work_dir>
"""
import json
import os
import sys
import traceback

import swhelpers as sw

PART_NAME = "mounting_plate"
VOLUME_TOLERANCE_REL = 1e-6


def run_cases(app, part_path, cases, density, baseline, warning_flag):
    """Drive each case on a reopened copy of the part. Returns (driven, detail).

    Nothing is saved: the part on disk stays the one that was accepted. Each case
    reopens the file so one case cannot ride on another's changes.
    """
    detail = []
    for case in cases:
        part = sw.open_part(app, part_path)
        entry = {"name": case["name"], "globals": case["globals"], "applied": {}}
        if part is None:
            entry["error"] = "could not open %s" % part_path
            detail.append(entry)
            continue

        for variable, value in case["globals"].items():
            entry["applied"][variable] = sw.set_global(part, variable, value)

        rebuild_ok, entry["rebuild"] = sw.rebuild(part, warning_flag)
        expected = case["expected"]["volume_mm3"]
        measured = sw.volume_mm3(part, density)
        solids = sw.body_count(part)
        error_rel = abs(measured - expected) / expected if expected else None

        entry.update(
            expected_volume_mm3=expected,
            measured_volume_mm3=measured,
            error_rel=error_rel,
            n_solids=solids,
            rebuild_ok=rebuild_ok,
            measured_baseline_instead=abs(measured - baseline) < abs(measured - expected),
            driven=bool(rebuild_ok and solids == 1 and error_rel is not None
                        and error_rel <= VOLUME_TOLERANCE_REL),
        )
        detail.append(entry)
        sw.close(app, part)

    return bool(detail) and all(c.get("driven") for c in detail), detail


def main():
    work_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    result = {"status": "error", "message": "", "cases": []}
    app = None
    try:
        if sw.solidworks_running():
            result["message"] = "SLDWORKS.exe is already running; refusing to attach to a session this script does not own"
            return

        g = json.loads(open(os.path.join(work_dir, "geometry.json")).read())
        oracle = json.loads(open(os.path.join(work_dir, "oracle.json")).read())

        app, callout, warning_flag = sw.connect()
        result["unattended"] = sw.last_unattended_journal()
        baseline = oracle["parts"][PART_NAME]["volume_mm3"]
        result["baseline_volume_mm3"] = baseline

        driven, result["cases"] = run_cases(
            app, os.path.join(work_dir, "%s.sldprt" % PART_NAME), oracle["redrive"],
            g["material"]["density"]["value"], baseline, warning_flag)

        result["status"] = "ok" if driven else "error"
        result["message"] = ("every parameter change drove the geometry to the oracle"
                            if driven else
                            "at least one parameter change did not drive the geometry")

    except Exception:
        result["message"] = "unhandled exception:\n" + traceback.format_exc()
    finally:
        sw.shutdown(app)
        with open(os.path.join(work_dir, "redrive_result.json"), "w") as handle:
            json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
