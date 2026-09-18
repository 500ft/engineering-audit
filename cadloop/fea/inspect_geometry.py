"""Import a cadloop IGES export into a running MAPDL session and report its extent.

Run this before writing any boundary condition: IGES import orientation and
scale are not otherwise known, and guessing them has cost real time on the CAD
side of this loop already. Connects to an already-running MAPDL gRPC server;
does not launch one.

Invoked as: python inspect_geometry.py <iges_path> [--ip IP] [--port PORT]
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("iges_path")
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50052)
    parser.add_argument("--result", default="geometry_inspection.json")
    args = parser.parse_args()

    from ansys.mapdl.core import Mapdl

    report = {"iges_path": args.iges_path, "status": "error", "message": ""}
    mapdl = None
    try:
        mapdl = Mapdl(ip=args.ip, port=args.port, start_instance=False)
        mapdl.clear()
        mapdl.aux15()
        mapdl.igesin(args.iges_path)
        mapdl.prep7()
        mapdl.nummrg("all")

        n_areas = mapdl.geometry.n_area
        n_lines = mapdl.geometry.n_line
        n_keypoints = mapdl.geometry.n_keypoint
        n_volumes = mapdl.geometry.n_volu

        # Bounding box: query keypoint locations directly, since geometry
        # extent is the one thing an APDL script cannot assume.
        mapdl.run("*GET,XMIN,KP,0,MNLOC,X")
        mapdl.run("*GET,XMAX,KP,0,MXLOC,X")
        mapdl.run("*GET,YMIN,KP,0,MNLOC,Y")
        mapdl.run("*GET,YMAX,KP,0,MXLOC,Y")
        mapdl.run("*GET,ZMIN,KP,0,MNLOC,Z")
        mapdl.run("*GET,ZMAX,KP,0,MXLOC,Z")
        bbox = {
            "x": [mapdl.parameters["XMIN"], mapdl.parameters["XMAX"]],
            "y": [mapdl.parameters["YMIN"], mapdl.parameters["YMAX"]],
            "z": [mapdl.parameters["ZMIN"], mapdl.parameters["ZMAX"]],
        }

        report.update({
            "status": "ok",
            "n_areas": n_areas,
            "n_lines": n_lines,
            "n_keypoints": n_keypoints,
            "n_volumes": n_volumes,
            "bounding_box": bbox,
        })
    except Exception as error:
        report["message"] = "%s: %s" % (type(error).__name__, error)

    # Deliberately does not call mapdl.exit(): this script connects to a
    # server it does not own, and the FEA run that follows reuses the same
    # session rather than paying MAPDL's startup cost twice.

    with open(args.result, "w") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
