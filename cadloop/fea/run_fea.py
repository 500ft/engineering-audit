#!/usr/bin/env python3
"""SOLIDWORKS export -> MAPDL -> images and a checked stress number. One command.

Workstation side. Launches MAPDL on the host, tunnels its gRPC port, imports the
IGES the CAD stage wrote, meshes it at several element sizes, solves, renders
images, and gates the peak stress against a closed-form stress-concentration
factor. Writes one result JSON and the PNGs beside it.

Why the oracle matters more than the pictures: a contour plot is the weakest
evidence this pipeline produces. A solve that converged on the wrong boundary
conditions, the wrong units or a mesh that never resolved the hole produces a
plausible, colourful, wrong image every time. So the images are rendered *and*
the peak stress at the hole is compared against Howland's finite-width plate
solution. The picture shows where the stress is; the oracle is what says the
number is right.

Why a mesh sweep rather than one solve: peak stress at a stress raiser is
mesh-dependent and converges from below. A single mesh cannot distinguish "the
model is right" from "the mesh was too coarse to see the peak". The sweep makes
that visible instead of hiding it, and ANSYS Student's 128k node ceiling is what
bounds the finest mesh.

usage: python run_fea.py [--part mounting_plate] [--pressure-mpa 1.0]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("CADLOOP_HOST_CONFIG",
                                 os.path.expanduser("~/.config/sw_pc_credentials.json")))
HERE = Path(__file__).resolve().parent

MAPDL_EXE = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe"
HOST_RUN_DIR = r"C:\CADLoop\fea_run"
HOST_CAD_DIR = r"C:\CADLoop\scaffold"
PORT = 50052

# ANSYS Student stops at 128k nodes for a structural solve. Staying under it is a
# licence constraint, not a modelling choice, so it bounds the sweep rather than
# being treated as a converged answer.
STUDENT_NODE_LIMIT = 128_000

STEEL_E_MPA = 200_000.0
STEEL_NU = 0.3

# The peak is at the hole edge. A fully fixed end face also raises stress in its
# own corners, and that concentration is an artefact of the restraint rather than
# the feature being checked, so the oracle reads the peak in a band around the
# hole and reports the global peak separately.
HOLE_BAND_MARGIN_MM = 4.0
END_EXCLUSION_MM = 8.0

# The correlation assumes a long plate under uniform far-field tension with free
# lateral edges. This model fixes one end face completely, which restrains Poisson
# contraction, and the plate is only 1.6 widths long, so the far field is not fully
# developed. Both push the measured peak *below* the correlation, and the measured
# bias has been about 8% on two independent geometries. The tolerance admits that
# known bias; it is not tight enough to call this a validation of the solver.
KT_TOLERANCE_REL = 0.12


# The SSH channel MAPDL was launched over. Closing it sends the server a hangup,
# so the handle is kept for the life of the run rather than being dropped.
_HELD: list[subprocess.Popen] = []


def config() -> dict:
    if not CONFIG_PATH.is_file():
        raise SystemExit(
            "host config not found at %s. See docs/host_setup.md; it holds a\n"
            "password, so it lives outside version control." % CONFIG_PATH)
    return json.loads(CONFIG_PATH.read_text())


def ssh_base(c: dict) -> list[str]:
    return ["ssh", "-i", c["ssh_key"], "%s@%s" % (c["ssh_user"], c["ssh_host"])]


def remote(c: dict, command: str, timeout: int = 60):
    return subprocess.run(ssh_base(c) + [command], capture_output=True, text=True,
                          timeout=timeout)


def kt_plate_central_hole(hole_d_mm: float, width_mm: float) -> float:
    """Heywood/Howland: finite-width plate, central hole, uniaxial tension.

    Referenced to the **net-section** nominal stress, P/((W-d)t) -- not the gross
    section. Getting this backwards is the easy mistake and it is worth being
    explicit about why this is the net-section form: referenced to gross stress,
    Kt must *rise* without bound as d/W -> 1, because the ligaments carrying the
    load vanish while the gross area does not change. This series *falls* with
    d/W, so it cannot be gross-referenced. Both conventions coincide at d/W -> 0,
    where the value is Kirsch's 3.0, so that limit cannot distinguish them.

    Valid to d/W = 0.5. Use `peak_stress_mpa` rather than this factor directly.
    """
    ratio = hole_d_mm / width_mm
    if not 0.0 < ratio <= 0.5:
        raise ValueError("d/W = %.3f is outside the correlation's range" % ratio)
    return 3.00 - 3.13 * ratio + 3.66 * ratio ** 2 - 1.53 * ratio ** 3


def peak_stress_mpa(hole_d_mm: float, width_mm: float, gross_stress_mpa: float) -> dict:
    """Expected peak stress at the hole, with the net-section conversion shown.

    The applied traction is the gross-section stress. Kt multiplies the *net*
    section stress, so the conversion W/(W-d) has to be applied or the prediction
    is low by that factor -- 32% for this plate.
    """
    kt_net = kt_plate_central_hole(hole_d_mm, width_mm)
    net_stress = gross_stress_mpa * width_mm / (width_mm - hole_d_mm)
    peak = kt_net * net_stress
    return {
        "kt_net_section": kt_net,
        "gross_stress_mpa": gross_stress_mpa,
        "net_stress_mpa": net_stress,
        "net_over_gross": width_mm / (width_mm - hole_d_mm),
        "expected_peak_mpa": peak,
        # What the solve's peak/applied ratio should come out as, for comparison
        # with the number the contour plot's legend shows.
        "expected_peak_over_gross": peak / gross_stress_mpa,
    }


def port_is_listening(c: dict) -> bool:
    out = remote(c, 'netstat -ano | findstr ":%d"' % PORT, timeout=30).stdout
    return "LISTENING" in out.upper()


def start_mapdl(c: dict, report: dict) -> bool:
    """Start MAPDL in gRPC mode on the host and wait for the port to listen.

    `-smp` is not cosmetic: in its default distributed mode the same executable
    left a wrapper process that never bound the port.
    """
    if port_is_listening(c):
        report["mapdl_launch"] = "already listening on %d" % PORT
        return True

    remote(c, 'if not exist "%s" mkdir "%s"' % (HOST_RUN_DIR, HOST_RUN_DIR))
    # A .lock left by a previous job stops MAPDL starting under the same job name.
    # It survives a crash or a killed session, so a run that never got to write a
    # log is the usual symptom: the process exits before opening one.
    remote(c, 'del /Q "%s\\%s*.lock"' % (HOST_RUN_DIR, "feajob"))
    # MAPDL reads the IGES from its own working directory.
    remote(c, 'copy /Y "%s\\%s" "%s\\"' % (HOST_CAD_DIR, report["iges_name"], HOST_RUN_DIR))

    # Launched over its own SSH channel, which is left open: `start /b` did not
    # keep the process alive once the invoking channel closed. The server never
    # returns, so this is not waited on -- the listening port is the signal.
    launch = ('cd /d %s && "%s" -grpc -smp -np 2 -port %d -j feajob > mapdl_launch.log 2>&1'
              % (HOST_RUN_DIR, MAPDL_EXE, PORT))
    _HELD.append(subprocess.Popen(ssh_base(c) + [launch],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    report["mapdl_launch_channel"] = "held open for the life of this run"

    deadline = time.time() + 240
    while time.time() < deadline:
        if port_is_listening(c):
            report["mapdl_launch"] = "started; port %d listening" % PORT
            return True
        time.sleep(5)
    report["mapdl_launch"] = "port %d never began listening" % PORT
    return False


def open_tunnel(c: dict) -> subprocess.Popen:
    """MAPDL binds 127.0.0.1 on the host, so the port is only reachable tunnelled."""
    process = subprocess.Popen(
        ["ssh", "-i", c["ssh_key"], "-N", "-L", "%d:127.0.0.1:%d" % (PORT, PORT),
         "%s@%s" % (c["ssh_user"], c["ssh_host"])],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    return process


def import_geometry(mapdl, iges_name: str, report: dict) -> list[int]:
    """IGES import yields surfaces, not a solid. Build the volume explicitly."""
    mapdl.clear()
    mapdl.prep7()
    mapdl.aux15()
    mapdl.igesin(iges_name)
    mapdl.prep7()
    mapdl.nummrg("all")
    mapdl.allsel()
    areas = [int(n) for n in mapdl.geometry.anum]
    report["imported_areas"] = len(areas)
    if not areas:
        raise RuntimeError("IGES import produced no areas")
    mapdl.va(*areas)
    mapdl.allsel()
    report["volumes_after_va"] = int(mapdl.geometry.n_volu)
    return areas


def mesh_and_solve(mapdl, size_mm: float, geometry: dict, pressure_mpa: float) -> dict:
    """One element size: mesh, apply boundary conditions, solve, measure."""
    import numpy as np

    length = geometry["length"]
    width = geometry["width"]
    hole_d = geometry["hole_diameter"]
    hole_x, hole_y = length / 2.0, width / 2.0

    mapdl.prep7()
    mapdl.vclear("all")
    mapdl.et(1, "SOLID186")
    mapdl.mp("EX", 1, STEEL_E_MPA)
    mapdl.mp("PRXY", 1, STEEL_NU)
    mapdl.esize(size_mm)
    # The plate-with-hole volume does not admit structured brick meshing.
    mapdl.mshape(1, "3D")
    mapdl.mshkey(0)
    mapdl.allsel()
    mapdl.vmesh("all")

    out = {"element_size_mm": size_mm,
           "n_elements": int(mapdl.mesh.n_elem),
           "n_nodes": int(mapdl.mesh.n_node)}
    if out["n_elements"] == 0:
        out["error"] = "meshing produced no elements"
        return out

    # Measure the orientation rather than assuming it. Every boundary condition
    # below names an axis, and d/W -- which the oracle depends on -- is decided by
    # which edge the load runs across. An IGES that came in rotated would still
    # solve, still look right, and be checked against the wrong Kt.
    coords_all = np.asarray(mapdl.mesh.nodes)
    extents = (coords_all.max(axis=0) - coords_all.min(axis=0)).tolist()
    out["bbox_mm"] = [float(v) for v in extents]
    expected_bbox = (geometry["length"], geometry["width"], geometry["thickness"])
    out["expected_bbox_mm"] = list(expected_bbox)
    if not all(abs(got - want) <= 0.5 for got, want in zip(extents, expected_bbox)):
        out["error"] = ("bounding box %s does not match length/width/thickness %s; "
                        "the part is not oriented as the boundary conditions and the "
                        "oracle assume" % (out["bbox_mm"], out["expected_bbox_mm"]))
        return out
    origin = coords_all.min(axis=0).tolist()
    out["origin_mm"] = [float(v) for v in origin]
    if any(abs(v) > 0.5 for v in origin):
        out["error"] = ("model origin is at %s, not 0,0,0; the X=0 and X=length "
                        "face selections would miss" % out["origin_mm"])
        return out
    if out["n_nodes"] > STUDENT_NODE_LIMIT:
        out["error"] = ("%d nodes exceeds the ANSYS Student limit of %d"
                        % (out["n_nodes"], STUDENT_NODE_LIMIT))
        return out

    # Fixed at X=0; uniform tension on the X=length face. Negative pressure is
    # tension, which is the sense Kt is defined in.
    mapdl.allsel()
    mapdl.nsel("S", "LOC", "X", 0)
    out["fixed_nodes"] = int(mapdl.mesh.n_node)
    mapdl.d("all", "all", 0)

    mapdl.allsel()
    mapdl.asel("S", "LOC", "X", length)
    out["loaded_areas"] = int(mapdl.geometry.n_area)
    mapdl.nsla("S", 1)
    mapdl.sfa("all", 1, "PRES", -pressure_mpa)

    mapdl.allsel()
    mapdl.run("/SOLU")
    mapdl.antype("STATIC")
    mapdl.solve()
    mapdl.finish()

    mapdl.post1()
    mapdl.set(1, 1)
    mapdl.allsel()

    coords = np.asarray(mapdl.mesh.nodes)
    eqv = np.asarray(mapdl.post_processing.nodal_eqv_stress())
    disp = np.asarray(mapdl.post_processing.nodal_displacement("NORM"))
    out["max_displacement_mm"] = float(disp.max())
    out["max_von_mises_mpa_global"] = float(eqv.max())

    if coords.shape[0] != eqv.shape[0]:
        out["error"] = ("node coordinate count %d does not match stress count %d"
                        % (coords.shape[0], eqv.shape[0]))
        return out

    # Peak in a band around the hole, away from the restrained and loaded ends.
    radial = np.hypot(coords[:, 0] - hole_x, coords[:, 1] - hole_y)
    band = ((radial <= hole_d / 2.0 + HOLE_BAND_MARGIN_MM)
            & (coords[:, 0] > END_EXCLUSION_MM)
            & (coords[:, 0] < length - END_EXCLUSION_MM))
    out["hole_band_nodes"] = int(band.sum())
    out["max_von_mises_mpa_at_hole"] = float(eqv[band].max()) if band.any() else None
    return out


def render(mapdl, out_dir: Path, tag: str, report: dict) -> None:
    """Contour plots. Rendered off-screen; failure here must not fail the solve."""
    images = {}
    jobs = (
        ("mesh", lambda path: mapdl.eplot(savefig=str(path), off_screen=True,
                                          show_edges=True, window_size=[1400, 1000])),
        ("von_mises", lambda path: mapdl.post_processing.plot_nodal_eqv_stress(
            savefig=str(path), off_screen=True, cpos="iso", show_edges=False,
            cmap="jet", window_size=[1400, 1000])),
        ("displacement", lambda path: mapdl.post_processing.plot_nodal_displacement(
            "NORM", savefig=str(path), off_screen=True, cpos="iso",
            show_edges=False, cmap="jet", window_size=[1400, 1000])),
    )
    for name, draw in jobs:
        path = out_dir / ("%s_%s.png" % (tag, name))
        try:
            draw(path)
            images[name] = path.name if path.is_file() else None
        except Exception as error:
            images[name] = "%s: %s" % (type(error).__name__, error)
    report["images"] = images


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", default="mounting_plate")
    parser.add_argument("--geometry", type=Path,
                        default=HERE.parent / "scaffold" / "geometry.json")
    parser.add_argument("--pressure-mpa", type=float, default=1.0)
    parser.add_argument("--element-sizes", default="5,3,2",
                        help="mm, coarse to fine; the sweep stops at the node limit")
    parser.add_argument("--out-dir", type=Path, default=HERE / "runs")
    args = parser.parse_args()

    g = json.loads(args.geometry.read_text())[args.part]
    geometry = {k: g[k]["value"] for k in ("length", "width", "thickness", "hole_diameter")}

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "error", "message": "", "part": args.part,
        "iges_name": "%s.igs" % args.part,
        "geometry_mm": geometry,
        "pressure_mpa": args.pressure_mpa,
        "material": {"E_mpa": STEEL_E_MPA, "nu": STEEL_NU},
        "meshes": [],
    }

    # The oracle, computed before anything is solved so it cannot be fitted to
    # the answer.
    prediction = peak_stress_mpa(geometry["hole_diameter"], geometry["width"],
                                 args.pressure_mpa)
    report["oracle"] = dict(
        prediction,
        source="Heywood/Howland finite-width plate, central hole, uniaxial tension",
        d_over_W=geometry["hole_diameter"] / geometry["width"],
        tolerance_rel=KT_TOLERANCE_REL,
    )

    c = config()
    tunnel = None
    mapdl = None
    try:
        if not start_mapdl(c, report):
            report["message"] = report["mapdl_launch"]
            return 1
        tunnel = open_tunnel(c)

        from ansys.mapdl.core import Mapdl
        mapdl = Mapdl(ip="127.0.0.1", port=PORT, start_instance=False, cleanup_on_exit=False)
        report["mapdl_version"] = str(mapdl.version)

        import_geometry(mapdl, report["iges_name"], report)

        best = None
        for size in [float(s) for s in args.element_sizes.split(",")]:
            result = mesh_and_solve(mapdl, size, geometry, args.pressure_mpa)
            report["meshes"].append(result)
            if "error" in result:
                break
            best = result
            render(mapdl, out_dir, "%s_h%g" % (args.part, size), report)

        if best is None:
            report["message"] = "no mesh size solved; see meshes[]"
            return 1

        peak = best.get("max_von_mises_mpa_at_hole")
        report["finest_solved"] = best
        if peak is None:
            report["message"] = "no nodes fell in the hole band; cannot check the peak"
            return 1

        expected = report["oracle"]["expected_peak_mpa"]
        error_rel = abs(peak - expected) / expected
        report["oracle"].update({
            "measured_peak_mpa": peak,
            "measured_peak_over_gross": peak / args.pressure_mpa,
            "error_rel": error_rel,
            "agrees": error_rel <= KT_TOLERANCE_REL,
        })
        report["status"] = "ok" if report["oracle"]["agrees"] else "error"
        report["message"] = (
            "solved; peak stress at the hole agrees with Heywood/Howland to %.1f%%"
            % (100 * error_rel) if report["oracle"]["agrees"] else
            "solved, but the peak stress disagrees with Heywood/Howland by %.1f%%"
            % (100 * error_rel))

    except Exception as error:
        import traceback
        report["message"] = "%s: %s" % (type(error).__name__, error)
        report["traceback"] = traceback.format_exc()
    finally:
        # The host process is not owned here beyond this run, but leaving a
        # licensed solver holding a seat is worse than a slow exit.
        try:
            if mapdl is not None:
                mapdl.exit()
        except Exception:
            pass
        if tunnel is not None:
            tunnel.terminate()
        for held in _HELD:
            held.terminate()
        (out_dir / ("%s_fea_result.json" % args.part)).write_text(
            json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
