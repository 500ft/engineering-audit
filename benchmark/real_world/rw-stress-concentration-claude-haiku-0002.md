# rw-stress-concentration-claude-haiku-0002: Claude Haiku Holed-Plate Capture (wrong nominal)

**Genuine verbatim `gold` capture of `claude-haiku-4-5-20251001`** run via the
`claude -p --model haiku` CLI with all tools disabled (no-tool self-calculation).
Raw bytes are stored under `captures/runs/` and referenced below by SHA-256; the
loader recomputes the hash and fails `P-01` on any edit. This is an elicited
real-world failure: Haiku applied a stress-concentration factor but computed the
nominal stress on the **wrong net area** (subtracting the circular hole area
`pi(d/2)^2` instead of the strip `d t`), reporting `sigma_nom ~= 129 MPa` instead
of `66.7 MPa` and a peak of `315 MPa` versus the validated `162.16 MPa` — a ~1.9x
**over**-prediction. MechAudit flags `FM-04`.

```json
{
  "case_id": "rw-stress-concentration-claude-haiku-0002",
  "schema_version": "0.3.0",
  "source_type": "real_world",
  "status": "complete",
  "source": {
    "kind": "api_model_run",
    "description": "Verbatim capture of claude-haiku-4-5-20251001 solving a finite-width holed-plate stress-concentration problem via `claude -p --model haiku` with all tools disabled (no-tool self-calculation). Raw bytes stored under captures/runs/ and referenced by SHA-256.",
    "provenance_tier": "gold",
    "raw_output_available": true,
    "model_name": "claude-haiku-4-5-20251001",
    "model_version": "claude-haiku-4-5-20251001",
    "run_date": "2026-06-25",
    "temperature": null,
    "run_settings": {"cli": "claude -p --model haiku", "disallowed_tools": ["Bash", "Edit", "Write", "Read", "WebSearch", "WebFetch"], "capture_protocol": "challenge"},
    "metadata_source": "self_report",
    "capture_protocol": "challenge",
    "provider": "anthropic",
    "artifacts": [
      {"kind": "raw_response", "path": "captures/runs/claude-haiku-4-5-20251001__sc-plate-hole-w100-t8-d25-p40kn__be7b8cc6cf26/output.txt", "sha256": "be7b8cc6cf269c9767bd887756870cd88da4a8c2c16ffa285336fc7ebb2a039c", "media_type": "text/plain"},
      {"kind": "prompt", "path": "captures/prompts/sc-plate-hole-w100-t8-d25-p40kn.txt", "sha256": "821bf96cc6c97585ee2d11b24704c94ec3eeaa44940b47f5b83abddb49b0596b", "media_type": "text/plain"}
    ]
  },
  "prompt_id": "sc_plate_hole_W100_t8_d25_P40kN",
  "problem_statement": "A flat steel plate of width W = 100 mm and thickness t = 8 mm has a central transverse circular hole of diameter d = 25 mm and carries an axial tensile force P = 40 kN. Find the maximum tensile stress at the edge of the hole. State the formula and your final numeric answer concisely. No calculator, no tools.",
  "llm_response": {
    "prompt": "captures/prompts/sc-plate-hole-w100-t8-d25-p40kn.txt",
    "response": "**Formula:**\n\n$$\\sigma_{max} = K_t \\times \\frac{F}{A_{net}}$$\n\nwhere $A_{net} = bt - \\pi\\left(\\frac{d}{2}\\right)^2$ and $K_t$ is the stress concentration factor.\n\n**Solution:**\n\n1. **Net cross-sectional area:**\n   - $A_{net} = (100)(8) - \\pi(12.5)^2 = 800 - 491 \\approx 309 \\text{ mm}^2$\n\n2. **Nominal stress (on net area):**\n   - $\\sigma_{nom} = \\frac{40,000}{309} \\approx 129 \\text{ MPa}$\n\n3. **Stress concentration factor:**\n   - For hole ratio $d/b = 25/100 = 0.25$, from standard tables: $K_t \\approx 2.44$\n\n4. **Maximum stress:**\n   - $\\sigma_{max} = 2.44 \\times 129 \\approx \\boxed{315 \\text{ MPa}}$\n\nThe stress concentration at the hole edge produces ~2.4× amplification over the nominal stress."
  },
  "expected_result": {
    "value": 162.158333,
    "unit": "MPa",
    "method": "sigma_max = Kt_net * sigma_net, with Kt_net = 2 + 0.284 s - 0.600 s^2 + 1.32 s^3 (s = 1 - d/W) per Peterson/Heywood (Pilkey Chart 4.1; Roark Table 17.1), and sigma_net = P / ((W - d) t). d/W = 0.25 => Kt_net = 2.432375, sigma_net = 66.667 MPa.",
    "required_assumptions": ["linear-elastic isotropic material", "central transverse circular hole", "uniaxial far-field tension", "Kt referenced to net-section nominal stress"]
  },
  "failure_modes": ["FM-04"],
  "formulas_used": [
    {"id": "eq1", "formula_id": "net_section_stress", "equation": "sigma_net = P / ((W - d) * t)", "purpose": "Compute net-section nominal stress", "variables": {"sigma_net": "net_section_stress", "P": "axial_force", "W": "plate_width", "d": "hole_diameter", "t": "thickness"}},
    {"id": "eq2", "formula_id": "stress_concentration_peak", "equation": "sigma_max = Kt_net * sigma_net", "purpose": "Apply stress-concentration factor to net-section stress", "variables": {"sigma_max": "peak_stress", "Kt_net": "stress_concentration_factor", "sigma_net": "net_section_stress"}}
  ],
  "inputs": {
    "plate_width": {"value": 100, "unit": "mm"},
    "hole_diameter": {"value": 25, "unit": "mm"},
    "thickness": {"value": 8, "unit": "mm"},
    "axial_force": {"value": 40, "unit": "kN"}
  },
  "outputs": [
    {"name": "peak_stress", "symbol": "sigma_max", "value": 315.0, "unit": "MPa", "source": "llm"},
    {"name": "net_section_stress", "symbol": "sigma_net", "value": 66.666667, "unit": "MPa", "source": "expected"},
    {"name": "peak_stress", "symbol": "sigma_max", "value": 162.158333, "unit": "MPa", "source": "expected"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md"},
  "notes": {
    "assumptions_stated": ["net-section nominal approach", "central transverse circular hole", "uniaxial tension"],
    "limitations": ["Genuine verbatim gold capture; raw bytes under captures/runs/, referenced by SHA-256.", "Model run via claude -p with all tools disabled, so model/version/date are self-reported, not provider-API metadata.", "Kt_net is the Heywood/Howland fit to Peterson's chart, valid for 0 < d/W < 1."],
    "reviewer_notes": "In-repo ground truth via mechaudit.stress_concentration.plate_with_hole: d/W = 0.25, Kt_net = 2.432375, sigma_net = 66.667 MPa, sigma_max = 162.158 MPa. Haiku picked a reasonable Kt (~2.44 vs 2.432) but computed the nominal on the wrong net area (bt - pi(d/2)^2 = 309 mm^2 instead of (W-d)t = 600 mm^2), so sigma_nom = 129 MPa instead of 66.7 MPa, and the peak came out 315 MPa, ~1.94x the true 162.16 MPa.",
    "expected_verifier_behavior": "Detect FM-04. The reported 315 MPa matches neither the net-section nominal (66.67 MPa) nor the validated peak (162.16 MPa), so the message should report a wrong Kt or wrong nominal."
  }
}
```

## Reference Solution (independent, in-repo)

```text
d/W = 25/100 = 0.25
s = 1 - d/W = 0.75
Kt_net = 2 + 0.284 s - 0.600 s^2 + 1.32 s^3 = 2.432375
sigma_net = 40000 N / ((100 - 25) mm * 8 mm) = 66.667 MPa
sigma_max = 2.432375 * 66.667 = 162.158 MPa
```

Haiku reported **315 MPa** — its `Kt` was fine (~2.44), but it computed the
nominal on the wrong net area `(b t - pi(d/2)^2)`, inflating `sigma_nom` to
129 MPa instead of 66.7 MPa. The peak is ~1.9x the true value. MechAudit flags
`FM-04`.
