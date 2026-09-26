"""Why does driving D3@Sketch1 change no geometry? Runs on the host.

The re-drive test shows PlateThickness (a feature dimension) driving and the two
plate sketch dimensions not. Either those dimensions are not driving dimensions,
or they are not the ones that control the rectangle. This lists every dimension
in the part with its driven state, which distinguishes the two.

Invoked on the host as: python probe_sketch_dims.py <work_dir>
"""
import json
import os
import sys
import traceback

import swhelpers as sw

RESULT = {"status": "error", "message": "", "features": []}


def main():
    work_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    app = None
    try:
        app, callout, warning_flag = sw.connect()
        part = sw.open_part(app, os.path.join(work_dir, "mounting_plate.sldprt"))
        if part is None:
            RESULT["message"] = "could not open mounting_plate.sldprt"
            return

        feature = part.FirstFeature
        while feature is not None:
            entry = {"feature": feature.Name, "type": feature.GetTypeName2, "dimensions": []}
            display = feature.GetFirstDisplayDimension
            while display is not None:
                dimension = display.GetDimension2(0)
                record = {}
                for label, attribute in (("full_name", "FullName"),
                                         ("short_name", None),
                                         ("value_mm", "SystemValue"),
                                         ("driven_state", "DrivenState"),
                                         ("read_only", "ReadOnly")):
                    try:
                        if attribute is None:
                            record[label] = sw.short_name(dimension)
                        else:
                            value = getattr(dimension, attribute)
                            record[label] = value / sw.MM if label == "value_mm" else value
                    except Exception as error:
                        record[label] = "%s: %s" % (type(error).__name__, error)
                entry["dimensions"].append(record)
                display = feature.GetNextDisplayDimension(display)
            if entry["dimensions"]:
                RESULT["features"].append(entry)
            feature = feature.GetNextFeature

        # Also: is the plate sketch fully defined, over-defined or under-defined?
        try:
            sketch = part.FeatureByName("Sketch1")
            RESULT["sketch1_constraint_state"] = sketch.GetSpecificFeature2.GetConstrainedStatus
        except Exception as error:
            RESULT["sketch1_constraint_state"] = "%s: %s" % (type(error).__name__, error)

        RESULT["status"] = "ok"
        RESULT["message"] = "probe complete"
        sw.close(app, part)

    except Exception:
        RESULT["message"] = "unhandled exception:\n" + traceback.format_exc()
    finally:
        sw.shutdown(app)
        with open(os.path.join(work_dir, "probe_sketch_dims_result.json"), "w") as handle:
            json.dump(RESULT, handle, indent=2)


if __name__ == "__main__":
    main()
