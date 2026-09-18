"""Solve a cadloop plate export as a linear-static solid FEA job.

Connects to an already-running MAPDL gRPC session with the plate's IGES
surfaces already imported and merged (see inspect_geometry.py) — the geometry
here has no volume, only the 8 surfaces IGES import produced, so the volume is
built explicitly before meshing with a structural solid element.

Boundary conditions assume the bounding box inspect_geometry.py reported for
this fixture: the length axis is X, spanning 0 to Length. This is not a
general-purpose loader; it is written for the plate-with-center-hole template.

Invoked as: python run_static_plate.py <length_mm> <pressure_mpa> [--ip IP] [--port PORT]
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("length_mm", type=float)
    parser.add_argument("pressure_mpa", type=float)
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50052)
    parser.add_argument("--element-size-mm", type=float, default=5.0)
    parser.add_argument("--youngs-modulus-mpa", type=float, default=200000.0)
    parser.add_argument("--poissons-ratio", type=float, default=0.3)
    parser.add_argument("--result", default="static_plate_result.json")
    args = parser.parse_args()

    from ansys.mapdl.core import Mapdl

    report = {"status": "error", "message": "", "inputs": vars(args)}
    mapdl = None
    try:
        mapdl = Mapdl(ip=args.ip, port=args.port, start_instance=False)

        mapdl.prep7()
        n_areas = mapdl.geometry.n_area
        if n_areas == 0:
            report["message"] = "no areas selected; run inspect_geometry.py against this session first"
            _write(report, args.result)
            return 1

        mapdl.allsel()
        area_numbers = [int(n) for n in mapdl.geometry.anum]
        mapdl.va(*area_numbers)

        mapdl.et(1, "SOLID186")
        mapdl.mp("EX", 1, args.youngs_modulus_mpa)
        mapdl.mp("PRXY", 1, args.poissons_ratio)
        mapdl.esize(args.element_size_mm)
        # The plate-with-hole volume's topology does not fit structured
        # brick meshing (mapdl's default); free tetrahedral meshing does.
        mapdl.mshape(1, "3D")
        mapdl.mshkey(0)
        mesh_status = mapdl.vmesh("all")
        report["mesh_status"] = str(mesh_status)

        n_elem = mapdl.mesh.n_elem
        n_node = mapdl.mesh.n_node
        report["n_elements"] = n_elem
        report["n_nodes"] = n_node
        if n_elem == 0 or n_node == 0:
            report["message"] = "meshing produced no elements"
            _write(report, args.result)
            return 1

        mapdl.allsel()
        mapdl.nsel("S", "LOC", "X", 0)
        fixed_count = mapdl.mesh.n_node
        mapdl.d("all", "all", 0)

        mapdl.allsel()
        mapdl.asel("S", "LOC", "X", args.length_mm)
        loaded_area_count = mapdl.geometry.n_area
        mapdl.nsla("S", 1)
        mapdl.sfa("all", 1, "PRES", args.pressure_mpa)
        report["fixed_node_count"] = fixed_count
        report["loaded_area_count"] = loaded_area_count

        mapdl.allsel()
        mapdl.run("/SOLU")
        mapdl.antype("STATIC")
        solve_output = mapdl.solve()
        mapdl.finish()
        report["solve_output_tail"] = str(solve_output)[-500:]

        mapdl.post1()
        mapdl.set(1, 1)
        max_displacement = float(mapdl.post_processing.nodal_displacement("NORM").max())
        max_von_mises = float(mapdl.post_processing.nodal_eqv_stress().max())
        report.update({
            "status": "ok",
            "message": "solved",
            "max_displacement_mm": max_displacement,
            "max_von_mises_mpa": max_von_mises,
        })

    except Exception as error:
        report["message"] = "%s: %s" % (type(error).__name__, error)

    _write(report, args.result)
    return 0 if report["status"] == "ok" else 1


def _write(report, path):
    with open(path, "w") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
