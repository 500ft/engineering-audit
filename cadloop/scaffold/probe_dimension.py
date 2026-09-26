"""Isolate why dimensioning a circle on a face fails. Runs on the host.

Two questions in one run, because host runs are expensive:
  1. What is swInputDimValOnCreate (id 10) actually set to? RoboRacer's
     unattended.py targets it. Answered: it was true on this host, which is what
     hung the run, and writing it false read back false. swhelpers.connect() now
     clears it via begin_unattended() and journals the read-back.
  2. Does AddDimension2 on a circle sketched on a face fail on its own, or only
     after earlier dimensions in the same part?

Invoked on the host as: python probe_dimension.py <work_dir>
"""
import json
import os
import sys
import traceback

import swhelpers as sw

RESULT = {"status": "error", "message": "", "toggle": {}, "steps": []}


def step(name, ok, detail=None):
    RESULT["steps"].append({"step": name, "ok": bool(ok), "detail": detail})
    return bool(ok)


def main():
    work_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    app = None
    try:
        app, callout, warning = sw.connect()

        # 1. read the toggle, without changing it
        try:
            value = bool(app.GetUserPreferenceToggle(10))
            RESULT["toggle"] = {"id": 10, "name": "swInputDimValOnCreate", "value": value,
                                "readable": True}
        except Exception as error:
            RESULT["toggle"] = {"id": 10, "readable": False, "error": str(error)}

        # 2. plate, then a circle on its top face, dimensioning nothing first
        part = sw.new_part(app)
        step("new_document", part is not None)
        sketcher = part.SketchManager

        step("select_front_plane", sw.select_plane(part, "Front Plane", callout))
        sketcher.InsertSketch(True)
        sketcher.CreateCornerRectangle(0.0, 0.0, 0.0, 80 * sw.MM, 50 * sw.MM, 0.0)
        sketcher.InsertSketch(True)
        boss = sw.extrude(part, 8)
        step("extrude", boss is not None, {"volume_mm3": sw.volume_mm3(part)})

        step("select_top_face", sw.select_face(part, (40, 25, 8), callout))
        sketcher.InsertSketch(True)
        sketcher.CreateCircleByRadius(40 * sw.MM, 25 * sw.MM, 0.0, 6 * sw.MM)

        # The failing call, with no prior dimension in this part.
        part.ClearSelection2(True)
        picked = part.Extension.SelectByID2("", "SKETCHSEGMENT", 46 * sw.MM, 25 * sw.MM,
                                            8 * sw.MM, False, 0, callout, 0)
        step("select_circle_segment", picked)
        try:
            display = part.AddDimension2(52 * sw.MM, 37 * sw.MM, 8 * sw.MM)
            step("add_dimension_no_prior", display is not None)
            if display is not None:
                dim = display.GetDimension2(0)
                sw.set_property(dim, "SystemValue", 12 * sw.MM)
                step("set_value", True, sw.short_name(dim))
        except Exception as error:
            step("add_dimension_no_prior", False, "%s: %s" % (type(error).__name__, error))

        RESULT["status"] = "ok"
        RESULT["message"] = "probe complete"
        sw.close(app, part)

    except Exception:
        RESULT["message"] = "unhandled exception:\n" + traceback.format_exc()
    finally:
        sw.shutdown(app)
        with open(os.path.join(work_dir, "probe_dimension_result.json"), "w") as handle:
            json.dump(RESULT, handle, indent=2)


if __name__ == "__main__":
    main()
