#!/usr/bin/env python3
"""Independent expectation for the scaffold part, built in CadQuery.

Runs on the workstation, not the host. This is the reference the SOLIDWORKS model
is gated against: a clean rebuild proves SOLIDWORKS raised no error, not that the
requested geometry was produced. Build the same part here that author_part.py
builds there, from the same geometry.json.

It also computes the expected volume for each parameter-change case in
redrive.json, so the re-drive test on the host has something independent to be
checked against rather than a number this script's own SOLIDWORKS run produced.

usage: python oracle.py [--geometry geometry.json] [--redrive redrive.json] [--out oracle.json]
"""
from __future__ import annotations
import argparse, copy, json
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent


def v(node):
    return node["value"]


def build(g):
    p = g["mounting_plate"]
    length, width = v(p["length"]), v(p["width"])
    thickness, hole = v(p["thickness"]), v(p["hole_diameter"])

    plate = cq.Workplane("XY").box(length, width, thickness, centered=False)
    bore = (cq.Workplane("XY")
            .center(length / 2, width / 2)
            .circle(hole / 2)
            .extrude(thickness))
    return plate.cut(bore)


def measure(solid):
    val = solid.val()
    bb = val.BoundingBox()
    volume = float(val.Volume())
    return {
        "volume_mm3": volume,
        "bbox_mm": [float(bb.xlen), float(bb.ylen), float(bb.zlen)],
        "n_solids": len(solid.solids().vals()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geometry", type=Path, default=HERE / "geometry.json")
    ap.add_argument("--redrive", type=Path, default=HERE / "redrive.json")
    ap.add_argument("--out", type=Path, default=HERE / "oracle.json")
    a = ap.parse_args()

    g = json.loads(a.geometry.read_text())
    density = v(g["material"]["density"])

    baseline = measure(build(g))
    out = {
        "density_kg_m3": density,
        "parts": {
            "mounting_plate": dict(baseline,
                                   mass_kg=baseline["volume_mm3"] * 1e-9 * density),
        },
        "redrive": [],
    }

    if a.redrive.is_file():
        for case in json.loads(a.redrive.read_text())["cases"]:
            changed = copy.deepcopy(g)
            for variable, change in case["set"].items():
                node = changed
                for key in change["path"]:
                    node = node[key]
                node["value"] = change["value"]
            out["redrive"].append({
                "name": case["name"],
                "globals": {variable: change["value"]
                            for variable, change in case["set"].items()},
                "expected": measure(build(changed)),
            })

    a.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
