"""Where do D1/D2 come from, and what makes the rectangle actually driven?

The re-drive test shows the plate sketch dimensions not driving. The saved part
holds four dimensions on two edges: D1/D2 driven, D3/D4 driving. This asks, in
one host run:

  A. Does CreateCornerRectangle produce dimensions on its own, before
     AddDimension2 is called at all?
  B. What is the sketch's constrained status at each step, so the value 3 seen in
     the saved part can be read against states whose meaning is known?
  C. If the pre-existing dimensions are deleted before adding ours, does the
     sketch become fully defined with ours driving?

Invoked on the host as: python probe_rectangle.py <work_dir>
"""
import json
import os
import sys
import traceback

import swhelpers as sw

RESULT = {"status": "error", "message": "", "steps": []}
LENGTH, WIDTH = 80.0, 50.0


def dims_of(part, sketch_name):
    """Every dimension on a sketch feature, with its driven state."""
    out = []
    feature = part.FeatureByName(sketch_name)
    if feature is None:
        return out
    display = feature.GetFirstDisplayDimension
    while display is not None:
        dimension = display.GetDimension2(0)
        out.append({"name": sw.short_name(dimension),
                    "value_mm": dimension.SystemValue / sw.MM,
                    "driven_state": dimension.DrivenState})
        display = feature.GetNextDisplayDimension(display)
    return out


def status_of(part, sketch_name):
    try:
        return part.FeatureByName(sketch_name).GetSpecificFeature2.GetConstrainedStatus
    except Exception as error:
        return "%s: %s" % (type(error).__name__, error)


def step(name, detail):
    RESULT["steps"].append({"step": name, "detail": detail})


def main():
    work_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    app = None
    try:
        app, callout, warning_flag = sw.connect()
        RESULT["unattended"] = sw.last_unattended_journal()

        # --- A/B: rectangle alone, then with our dimensions added ---
        part = sw.new_part(app)
        sketcher = part.SketchManager
        sw.select_plane(part, "Front Plane", callout)
        sketcher.InsertSketch(True)

        # An empty sketch, for a known under-defined reference value.
        step("empty_sketch", {"status": status_of(part, "Sketch1")})

        sketcher.CreateCornerRectangle(0.0, 0.0, 0.0, LENGTH * sw.MM, WIDTH * sw.MM, 0.0)
        step("after_rectangle", {"status": status_of(part, "Sketch1"),
                                 "dimensions": dims_of(part, "Sketch1")})

        first = sw.dimension_segment(part, callout, (LENGTH / 2, 0.0, 0.0),
                                     (LENGTH / 2, -10.0, 0.0), LENGTH)
        step("after_length_dim", {"added": first, "status": status_of(part, "Sketch1"),
                                  "dimensions": dims_of(part, "Sketch1")})

        second = sw.dimension_segment(part, callout, (0.0, WIDTH / 2, 0.0),
                                      (-10.0, WIDTH / 2, 0.0), WIDTH)
        step("after_width_dim", {"added": second, "status": status_of(part, "Sketch1"),
                                 "dimensions": dims_of(part, "Sketch1")})
        sketcher.InsertSketch(True)
        sw.close(app, part)

        # --- C: rectangle, delete whatever it brought, then add ours ---
        part = sw.new_part(app)
        sketcher = part.SketchManager
        sw.select_plane(part, "Front Plane", callout)
        sketcher.InsertSketch(True)
        sketcher.CreateCornerRectangle(0.0, 0.0, 0.0, LENGTH * sw.MM, WIDTH * sw.MM, 0.0)

        deleted = []
        for existing in dims_of(part, "Sketch1"):
            part.ClearSelection2(True)
            picked = part.Extension.SelectByID2(existing["name"], "DIMENSION",
                                                0, 0, 0, False, 0, callout, 0)
            removed = bool(part.EditDelete()) if picked else False
            deleted.append({"name": existing["name"], "selected": picked, "deleted": removed})
        step("after_delete", {"deleted": deleted, "status": status_of(part, "Sketch1"),
                              "dimensions": dims_of(part, "Sketch1")})

        clean_first = sw.dimension_segment(part, callout, (LENGTH / 2, 0.0, 0.0),
                                           (LENGTH / 2, -10.0, 0.0), LENGTH)
        clean_second = sw.dimension_segment(part, callout, (0.0, WIDTH / 2, 0.0),
                                            (-10.0, WIDTH / 2, 0.0), WIDTH)
        step("clean_dims_added", {"added": [clean_first, clean_second],
                                  "status": status_of(part, "Sketch1"),
                                  "dimensions": dims_of(part, "Sketch1")})
        sketcher.InsertSketch(True)
        boss = sw.extrude(part, 8.0)
        step("extrude", {"volume_mm3": sw.volume_mm3(part)})

        # Does driving the length now actually move the geometry?
        accepted, written = sw.write_equations(
            part,
            ['"PlateLength"= %gmm' % LENGTH, '"PlateWidth"= %gmm' % WIDTH],
            [(clean_first, '"PlateLength"'), (clean_second, '"PlateWidth"')])
        sw.set_global(part, "PlateLength", 100.0)
        sw.rebuild(part, warning_flag)
        step("redrive_in_place", {"equations_accepted": accepted,
                                  "volume_mm3": sw.volume_mm3(part),
                                  "expected_mm3": 100.0 * WIDTH * 8.0,
                                  "dimensions": dims_of(part, "Sketch1")})
        sw.close(app, part)

        RESULT["status"] = "ok"
        RESULT["message"] = "probe complete"

    except Exception:
        RESULT["message"] = "unhandled exception:\n" + traceback.format_exc()
    finally:
        sw.shutdown(app)
        with open(os.path.join(work_dir, "probe_rectangle_result.json"), "w") as handle:
            json.dump(RESULT, handle, indent=2)


if __name__ == "__main__":
    main()
