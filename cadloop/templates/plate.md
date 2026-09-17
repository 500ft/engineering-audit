# Template contract — `plate.sldprt`

A rectangular plate with one through hole, used as the loop's reference
fixture. `author_template.py` creates it; `worker.py` drives it.

## Declared global variables

A job may set only these names. Values must carry explicit units (`"150mm"`).

| Variable | Authored default | Drives |
| --- | --- | --- |
| `Length` | `100mm` | profile-sketch horizontal dimension |
| `Width` | `60mm` | profile-sketch vertical dimension |
| `PlateThickness` | `5mm` | boss-extrude depth |
| `HoleDiameter` | `8mm` | hole-sketch circle diameter |

`Thickness` is not usable as a variable name: the equation manager rejects the
declaration and returns `-1`, and one rejected equation invalidates the rest of
the batch. `PlateThickness` is the substitute.

## Acceptance oracle

```
V = (Length * Width - pi * HoleDiameter^2 / 4) * PlateThickness
```

`plate_with_center_hole` in `volume.py`. At the authored defaults this is
29 748.673 mm³, which matched the measured mass properties to five decimal
places on first authoring.

The oracle constrains volume only. It does not detect a hole placed off centre,
because moving the hole does not change the volume. Hole position is currently
held by sketch dimensions in the template, not by an independent check.

## Known gap

`SketchAddConstraints("sgCOINCIDENT")` returns false when authoring, so the
profile sketch's corner is not anchored to the origin and the sketch is
under-defined. SOLIDWORKS rebuilds it without complaint and the authored
geometry measures correctly, but an under-defined profile is free to move under
a future parameter change. Anchoring it is tracked in `ROADMAP.md`.
