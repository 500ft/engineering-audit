# rw-stress-concentration-claude-haiku-0003: Claude Haiku Holed-Plate Capture (wrong Kt)

**Genuine verbatim `gold` capture of `claude-haiku-4-5-20251001`** run via the
`claude -p --model haiku` CLI with all tools disabled (no-tool self-calculation).
Raw bytes are stored under `captures/runs/` and referenced below by SHA-256; the
loader recomputes the hash and fails `P-01` on any edit. This is a clean Kt
error: Haiku got the net section right (`sigma_net = 62.5 MPa`) but used the
Kirsch infinite-plate `Kt = 3.0` instead of the finite-width factor `Kt_net =
2.519`, reporting `187.5 MPa` versus the validated `157.44 MPa`. MechAudit flags
`FM-04`.

```json
{
  "case_id": "rw-stress-concentration-claude-haiku-0003",
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
      {"kind": "raw_response", "path": "captures/runs/claude-haiku-4-5-20251001__sc-plate-hole-w80-t5-d16-p20kn__e234a02ce140/output.txt", "sha256": "e234a02ce140f0e97dcd6c054a74f1d7375a02def2b600df6eb330ab07c6fb94", "media_type": "text/plain"},
      {"kind": "prompt", "path": "captures/prompts/sc-plate-hole-w80-t5-d16-p20kn.txt", "sha256": "8e1422463df75e7ebe70121b2596df335c81762fd1ad0a65e679da608cf0928a", "media_type": "text/plain"}
    ]
  },
  "prompt_id": "sc_plate_hole_W80_t5_d16_P20kN",
  "problem_statement": "A flat steel plate of width W = 80 mm and thickness t = 5 mm has a central transverse circular hole of diameter d = 16 mm and carries an axial tensile force P = 20 kN. Find the maximum tensile stress at the edge of the hole. State the formula and your final numeric answer concisely. No calculator, no tools.",
  "llm_response": {
    "prompt": "captures/prompts/sc-plate-hole-w80-t5-d16-p20kn.txt",
    "response": "**Formula:**\n$$\\sigma_{max} = K_t \\cdot \\frac{P}{A_{net}}$$\n\nwhere K_t is the stress concentration factor (≈ 3.0 for a circular hole in tension) and A_net is the net cross-sectional area.\n\n**Calculation:**\n\nNet area: A_net = (W − d) × t = (80 − 16) × 5 = 64 × 5 = **320 mm²**\n\nNominal stress: σ_nom = P / A_net = 20,000 N / 320 mm² = **62.5 MPa**\n\nMaximum stress: σ_max = 3.0 × 62.5 = **187.5 MPa**"
  },
  "expected_result": {
    "value": 157.44,
    "unit": "MPa",
    "method": "sigma_max = Kt_net * sigma_net, with Kt_net = 2 + 0.284 s - 0.600 s^2 + 1.32 s^3 (s = 1 - d/W) per Peterson/Heywood (Pilkey Chart 4.1; Roark Table 17.1), and sigma_net = P / ((W - d) t). d/W = 0.2 => Kt_net = 2.51904, sigma_net = 62.5 MPa.",
    "required_assumptions": ["linear-elastic isotropic material", "central transverse circular hole", "uniaxial far-field tension", "Kt referenced to net-section nominal stress", "finite-width (not infinite-plate Kt = 3.0)"]
  },
  "failure_modes": ["FM-04"],
  "formulas_used": [
    {"id": "eq1", "formula_id": "net_section_stress", "equation": "sigma_net = P / ((W - d) * t)", "purpose": "Compute net-section nominal stress", "variables": {"sigma_net": "net_section_stress", "P": "axial_force", "W": "plate_width", "d": "hole_diameter", "t": "thickness"}},
    {"id": "eq2", "formula_id": "stress_concentration_peak", "equation": "sigma_max = Kt_net * sigma_net", "purpose": "Apply stress-concentration factor to net-section stress", "variables": {"sigma_max": "peak_stress", "Kt_net": "stress_concentration_factor", "sigma_net": "net_section_stress"}}
  ],
  "inputs": {
    "plate_width": {"value": 80, "unit": "mm"},
    "hole_diameter": {"value": 16, "unit": "mm"},
    "thickness": {"value": 5, "unit": "mm"},
    "axial_force": {"value": 20, "unit": "kN"}
  },
  "outputs": [
    {"name": "net_section_stress", "symbol": "sigma_net", "value": 62.5, "unit": "MPa", "source": "llm"},
    {"name": "peak_stress", "symbol": "sigma_max", "value": 187.5, "unit": "MPa", "source": "llm"},
    {"name": "net_section_stress", "symbol": "sigma_net", "value": 62.5, "unit": "MPa", "source": "expected"},
    {"name": "peak_stress", "symbol": "sigma_max", "value": 157.44, "unit": "MPa", "source": "expected"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md"},
  "notes": {
    "assumptions_stated": ["net-section nominal approach", "central transverse circular hole", "uniaxial tension", "Kt approx 3.0 (incorrect: that is the infinite-plate value)"],
    "limitations": ["Genuine verbatim gold capture; raw bytes under captures/runs/, referenced by SHA-256.", "Model run via claude -p with all tools disabled, so model/version/date are self-reported, not provider-API metadata.", "Kt_net is the Heywood/Howland fit to Peterson's chart, valid for 0 < d/W < 1."],
    "reviewer_notes": "In-repo ground truth via mechaudit.stress_concentration.plate_with_hole: d/W = 0.2, Kt_net = 2.519040, sigma_net = 62.5 MPa, sigma_max = 157.44 MPa. Haiku computed the net section correctly (sigma_net = 62.5 MPa) but used the Kirsch infinite-plate Kt = 3.0 instead of the finite-width Kt_net = 2.519, so the peak came out 187.5 MPa, ~1.19x the true 157.44 MPa (over-prediction).",
    "expected_verifier_behavior": "Detect FM-04. The reported 187.5 MPa matches neither the net-section nominal (62.5 MPa) nor the validated peak (157.44 MPa), so the message should report a wrong Kt or wrong nominal (correct Kt_net = 2.519)."
  }
}
```

## Reference Solution (independent, in-repo)

```text
d/W = 16/80 = 0.2
s = 1 - d/W = 0.8
Kt_net = 2 + 0.284 s - 0.600 s^2 + 1.32 s^3 = 2.519040
sigma_net = 20000 N / ((80 - 16) mm * 5 mm) = 62.5 MPa
sigma_max = 2.519040 * 62.5 = 157.44 MPa
```

Haiku reported **187.5 MPa** — the net section was right, but it used the Kirsch
infinite-plate `Kt = 3.0` instead of the finite-width `Kt_net = 2.519`. The peak
is ~1.19x the true value. MechAudit flags `FM-04`.
