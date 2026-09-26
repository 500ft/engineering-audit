"""Name the equation behind `Equations error_code 1`. Runs on the host.

The rebuild walk reports the Equations feature in error while the measured
volume matches the oracle exactly, and the by-reference warning flag says it is
not a warning. EquationMgr.Status(i) attributes that to a single equation;
without it the error is only a feature name.

Invoked on the host as: python probe_equations.py <work_dir>
"""
import json
import os
import sys
import traceback

import swhelpers as sw

RESULT = {"status": "error", "message": "", "equations": [], "features": []}


def main():
    work_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    app = None
    try:
        app, callout, warning_flag = sw.connect()
        part = sw.open_part(app, os.path.join(work_dir, "mounting_plate.sldprt"))
        if part is None:
            RESULT["message"] = "could not open mounting_plate.sldprt"
            return

        manager = part.GetEquationMgr
        for index in range(manager.GetCount):
            entry = {"index": index, "equation": manager.Equation(index)}
            for label, attribute in (("status", "Status"), ("value", "Value")):
                try:
                    entry[label] = getattr(manager, attribute)(index)
                except Exception as error:
                    entry[label] = "%s: %s" % (type(error).__name__, error)
            RESULT["equations"].append(entry)

        # Walk every feature, in error or not, so the picture is not partial.
        feature = part.FirstFeature
        while feature is not None:
            code = feature.GetErrorCode2(warning_flag)
            code = code[0] if isinstance(code, tuple) else code
            RESULT["features"].append({
                "name": feature.Name,
                "type": feature.GetTypeName2,
                "error_code": code,
                "warning": bool(getattr(warning_flag, "value", False)) if code else None,
            })
            feature = feature.GetNextFeature

        RESULT["rebuild"] = sw.rebuild(part, warning_flag)[1]
        RESULT["volume_mm3"] = sw.volume_mm3(part)
        RESULT["status"] = "ok"
        RESULT["message"] = "probe complete"
        sw.close(app, part)

    except Exception:
        RESULT["message"] = "unhandled exception:\n" + traceback.format_exc()
    finally:
        sw.shutdown(app)
        with open(os.path.join(work_dir, "probe_equations_result.json"), "w") as handle:
            json.dump(RESULT, handle, indent=2)


if __name__ == "__main__":
    main()
