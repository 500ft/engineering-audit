"""Author the scaffold part in SOLIDWORKS and gate it on the oracle. Runs on the host.

Copy this file, geometry.json and oracle.py to start a new part. The traps live in
swhelpers.py, so what remains here is the geometry and the acceptance check.

To adapt:
  1. Put your dimensions in geometry.json, one evidence_state per value.
  2. Build the same shape in oracle.py so there is something to be checked against.
  3. Replace build_part() below. Keep one closed contour per feature.
  4. Name the global variables your register should own in the equations block.

Invoked on the host as: python author_part.py <work_dir>
"""
import json
import os
import sys
import traceback

import redrive
import swhelpers as sw

PART_NAME = "mounting_plate"
VOLUME_TOLERANCE_REL = 1e-6

RESULT = {"status": "error", "message": "", "stages": [], "part": {}}


def stage(name, ok, detail=None):
    RESULT["stages"].append({"stage": name, "ok": bool(ok), "detail": detail})
    return bool(ok)


def build_part(part, g, callout):
    """Plate with a centred through hole, driven by named global variables.

    Two features, because a sketch may hold only one closed contour: the plate is
    extruded, then the bore is cut from the top face. Cutting from a face rather
    than a datum plane means the default cut direction runs into the body.
    """
    p = g[PART_NAME]
    length = p["length"]["value"]
    width = p["width"]["value"]
    thickness = p["thickness"]["value"]
    hole = p["hole_diameter"]["value"]

    sketcher = part.SketchManager

    # --- plate ---
    stage("select_front_plane", sw.select_plane(part, "Front Plane", callout))
    sketcher.InsertSketch(True)
    sketcher.CreateCornerRectangle(0.0, 0.0, 0.0, length * sw.MM, width * sw.MM, 0.0)
    # The rectangle tool dimensions its own rectangle; those dimensions fix the
    # geometry and would leave ours driving nothing. See clear_sketch_dimensions.
    cleared = sw.clear_sketch_dimensions(part, "Sketch1", callout)
    stage("clear_rectangle_dimensions", not cleared["remaining"], cleared)
    length_dim = sw.dimension_segment(part, callout,
                                      pick_mm=(length / 2, 0.0, 0.0),
                                      place_mm=(length / 2, -10.0, 0.0),
                                      value_mm=length)
    width_dim = sw.dimension_segment(part, callout,
                                     pick_mm=(0.0, width / 2, 0.0),
                                     place_mm=(-10.0, width / 2, 0.0),
                                     value_mm=width)
    stage("dimension_plate", bool(length_dim and width_dim), [length_dim, width_dim])
    sketcher.InsertSketch(True)

    boss = sw.extrude(part, thickness)
    stage("extrude_plate", boss is not None, {"volume_mm3": sw.volume_mm3(part)})
    thickness_dim = sw.feature_depth_name(boss)

    # --- bore, from the top face so the cut runs into the body ---
    stage("select_top_face",
          sw.select_face(part, (length / 2, width / 2, thickness), callout))
    sketcher.InsertSketch(True)
    sketcher.CreateCircleByRadius(length / 2 * sw.MM, width / 2 * sw.MM, 0.0,
                                  hole / 2 * sw.MM)
    cleared = sw.clear_sketch_dimensions(part, "Sketch2", callout)
    stage("clear_circle_dimensions", not cleared["remaining"], cleared)
    hole_dim = sw.dimension_segment(part, callout,
                                    pick_mm=(length / 2 + hole / 2, width / 2, thickness),
                                    place_mm=(length / 2 + hole, width / 2 + hole, thickness),
                                    value_mm=hole)
    stage("dimension_hole", bool(hole_dim), hole_dim)
    sketcher.InsertSketch(True)
    stage("cut_bore", sw.cut_through_all(part) is not None,
          {"volume_mm3": sw.volume_mm3(part)})

    # --- let the register own the design, not the sketch ---
    accepted, written = sw.write_equations(
        part,
        ['"PlateLength"= %gmm' % length,
         '"PlateWidth"= %gmm' % width,
         '"PlateThickness"= %gmm' % thickness,   # "Thickness" alone is reserved
         '"HoleDiameter"= %gmm' % hole],
        [(length_dim, '"PlateLength"'),
         (width_dim, '"PlateWidth"'),
         (thickness_dim, '"PlateThickness"'),
         (hole_dim, '"HoleDiameter"')],
    )
    stage("equations", accepted, written)


def main():
    work_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    app = None
    try:
        if sw.solidworks_running():
            RESULT["message"] = "SLDWORKS.exe is already running; refusing to attach to a session this script does not own"
            return

        g = json.loads(open(os.path.join(work_dir, "geometry.json")).read())
        oracle = json.loads(open(os.path.join(work_dir, "oracle.json")).read())
        density = g["material"]["density"]["value"]
        expected = oracle["parts"][PART_NAME]["volume_mm3"]

        app, callout, warning_flag = sw.connect()
        RESULT["unattended"] = sw.last_unattended_journal()
        part = sw.new_part(app)
        if not stage("new_document", part is not None):
            RESULT["message"] = "NewDocument returned nothing"
            return

        build_part(part, g, callout)

        paths = {
            "sldprt": os.path.join(work_dir, "%s.sldprt" % PART_NAME),
            "step": os.path.join(work_dir, "%s.step" % PART_NAME),
            # IGES as well: MAPDL has no reliable STEP reader, and the FEA stage
            # imports IGES through AUX15/IGESIN.
            "iges": os.path.join(work_dir, "%s.igs" % PART_NAME),
            "bmp": os.path.join(work_dir, "%s.bmp" % PART_NAME),
        }
        for kind in ("sldprt", "step", "iges"):
            RESULT["part"]["%s_written" % kind] = sw.save_as(part, paths[kind])
        RESULT["part"]["preview_written"] = sw.preview(part, paths["bmp"])
        sw.close(app, part)

        # Acceptance is measured on the reopened file, not the session that built
        # it: see sw.rebuild on why in-session rebuild state is unusable here,
        # and because what ships is the file, not the session.
        part = sw.open_part(app, paths["sldprt"])
        if not stage("reopen", part is not None, paths["sldprt"]):
            RESULT["message"] = "saved part could not be reopened"
            return

        rebuild_ok, rebuild_detail = sw.rebuild(part, warning_flag)
        stage("rebuild", rebuild_ok, rebuild_detail)

        measured = sw.volume_mm3(part, density)
        solids = sw.body_count(part)
        error_rel = abs(measured - expected) / expected if expected else None
        oracle_match = (rebuild_ok and solids == 1 and error_rel is not None
                        and error_rel <= VOLUME_TOLERANCE_REL)

        RESULT["part"].update({
            "measured_volume_mm3": measured,
            "oracle_volume_mm3": expected,
            "error_rel": error_rel,
            "tolerance_rel": VOLUME_TOLERANCE_REL,
            "n_solids": solids,
            "measured_mass_kg": measured * 1e-9 * density,
            "oracle_match": oracle_match,
            "rebuild_ok": rebuild_ok,
            "rebuild": rebuild_detail,
        })

        # The oracle alone cannot see equations that drive nothing: the part was
        # drawn at the intended size, so it measures right while being unusable
        # as a parametric model. Acceptance therefore includes the re-drive, and
        # is decided only once that has run.
        sw.close(app, part)
        part = None
        driven, RESULT["redrive"] = redrive.run_cases(
            app, paths["sldprt"], oracle["redrive"], density, expected, warning_flag)
        stage("redrive", driven, RESULT["redrive"])

        accepted = oracle_match and driven
        RESULT["part"]["equations_drive"] = driven
        RESULT["part"]["accepted"] = accepted
        stage("accepted", accepted, RESULT["part"])
        RESULT["status"] = "ok" if accepted else "error"
        RESULT["message"] = (
            "reopened part rebuilds clean, matches the oracle, and its equations drive it"
            if accepted else
            "rejected: oracle mismatch, dirty rebuild, or equations that drive nothing")

    except Exception:
        RESULT["message"] = "unhandled exception:\n" + traceback.format_exc()
    finally:
        sw.shutdown(app)
        with open(os.path.join(work_dir, "author_result.json"), "w") as handle:
            json.dump(RESULT, handle, indent=2)


if __name__ == "__main__":
    main()
