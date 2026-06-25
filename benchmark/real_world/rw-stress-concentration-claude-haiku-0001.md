# rw-stress-concentration-claude-haiku-0001: Claude Haiku Holed-Plate Capture (concentration omitted)

**Genuine verbatim `gold` capture of `claude-haiku-4-5-20251001`** run via the
`claude -p --model haiku` CLI with all tools disabled, so the model did its own
no-tool calculation. The raw bytes are stored under `captures/runs/` and
referenced below by SHA-256; the loader recomputes the hash and fails `P-01` on
any edit. This is an **elicited real-world failure**, not a synthetic control:
the expected answer is the in-repo Kt-validated `sigma_max`, and MechAudit flags
`FM-04` because the model omitted the stress concentration **and** used the wrong
net area (subtracting the circular hole *area* `pi(d/2)^2` instead of the strip
`d t`), under-predicting the true peak by ~2x.

```json
{
  "case_id": "rw-stress-concentration-claude-haiku-0001",
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
      {"kind": "raw_response", "path": "captures/runs/claude-haiku-4-5-20251001__sc-plate-hole-w60-t6-d12-p18kn__11230072d29f/output.txt", "sha256": "11230072d29ff7fc2b14b4fd229c19e592246c1f8a6481bb4f79b18fb009f3dc", "media_type": "text/plain"},
      {"kind": "prompt", "path": "captures/prompts/sc-plate-hole-w60-t6-d12-p18kn.txt", "sha256": "f739ee9b225a3282241f90388e170a01d83726ba49ebeb2d6c78b6341d91410e", "media_type": "text/plain"}
    ]
  },
  "prompt_id": "sc_plate_hole_W60_t6_d12_P18kN",
  "problem_statement": "A flat steel plate of width W = 60 mm and thickness t = 6 mm has a central transverse circular hole of diameter d = 12 mm and carries an axial tensile force P = 18 kN. Find the maximum tensile stress at the edge of the hole. State the formula and your final numeric answer concisely. No calculator, no tools.",
  "llm_response": {
    "prompt": "captures/prompts/sc-plate-hole-w60-t6-d12-p18kn.txt",
    "response": "**Formula:**\n\nMaximum tensile stress at the net section (stress concentration, nominal approach):\n\n$$\\sigma = \\frac{P}{A_{net}} = \\frac{P}{(W \\times t) - \\pi(d/2)^2}$$\n\nWhere:\n- P = 18,000 N (load)\n- W = 60 mm (width)\n- t = 6 mm (thickness)  \n- d = 12 mm (hole diameter)\n\n**Calculation:**\n\nNet area:\n- Gross area = 60 × 6 = 360 mm²\n- Hole area = π(6)² = 36π ≈ 113.1 mm²\n- A_net = 360 − 113.1 = 246.9 mm²\n\nStress:\n$$\\sigma = \\frac{18,000}{246.9} \\approx 72.9 \\text{ MPa}$$\n\n**Answer: σ_max ≈ 73 MPa** (or 72.9 MPa for more precision)"
  },
  "expected_result": {
    "value": 157.44,
    "unit": "MPa",
    "method": "sigma_max = Kt_net * sigma_net, with Kt_net = 2 + 0.284 s - 0.600 s^2 + 1.32 s^3 (s = 1 - d/W) per Peterson/Heywood (Pilkey Chart 4.1; Roark Table 17.1), and sigma_net = P / ((W - d) t). d/W = 0.2 => Kt_net = 2.51904, sigma_net = 62.5 MPa.",
    "required_assumptions": ["linear-elastic isotropic material", "central transverse circular hole", "uniaxial far-field tension", "Kt referenced to net-section nominal stress"]
  },
  "failure_modes": ["FM-04"],
  "formulas_used": [
    {"id": "eq1", "formula_id": "net_section_stress", "equation": "sigma_net = P / ((W - d) * t)", "purpose": "Compute net-section nominal stress", "variables": {"sigma_net": "net_section_stress", "P": "axial_force", "W": "plate_width", "d": "hole_diameter", "t": "thickness"}},
    {"id": "eq2", "formula_id": "stress_concentration_peak", "equation": "sigma_max = Kt_net * sigma_net", "purpose": "Apply stress-concentration factor to net-section stress", "variables": {"sigma_max": "peak_stress", "Kt_net": "stress_concentration_factor", "sigma_net": "net_section_stress"}}
  ],
  "inputs": {
    "plate_width": {"value": 60, "unit": "mm"},
    "hole_diameter": {"value": 12, "unit": "mm"},
    "thickness": {"value": 6, "unit": "mm"},
    "axial_force": {"value": 18, "unit": "kN"}
  },
  "outputs": [
    {"name": "peak_stress", "symbol": "sigma_max", "value": 72.9, "unit": "MPa", "source": "llm"},
    {"name": "net_section_stress", "symbol": "sigma_net", "value": 62.5, "unit": "MPa", "source": "expected"},
    {"name": "peak_stress", "symbol": "sigma_max", "value": 157.44, "unit": "MPa", "source": "expected"}
  ],
  "units": {"system": "SI", "canonical_outputs": {"stress": "MPa"}},
  "tolerance": {"relative": 0.005, "absolute": null, "policy": "docs/tolerance_policy.md"},
  "notes": {
    "assumptions_stated": ["net-section nominal approach", "central transverse circular hole", "uniaxial tension"],
    "limitations": ["Genuine verbatim gold capture; raw bytes under captures/runs/, referenced by SHA-256.", "Model run via claude -p with all tools disabled, so model/version/date are self-reported, not provider-API metadata.", "Kt_net is the Heywood/Howland fit to Peterson's chart, valid for 0 < d/W < 1."],
    "reviewer_notes": "In-repo ground truth via mechaudit.stress_concentration.plate_with_hole: d/W = 0.2, Kt_net = 2.519040, sigma_net = 62.5 MPa, sigma_max = 157.44 MPa. Haiku omitted the stress concentration entirely AND used the wrong net area (subtracted the circular hole area pi(d/2)^2 = 113.1 mm^2 instead of the transverse strip d*t = 72 mm^2), reporting 72.9 MPa. That under-predicts the true peak by ~2.16x, a dangerous non-conservative error.",
    "expected_verifier_behavior": "Detect FM-04. The reported 72.9 MPa is neither the net-section nominal sigma_net = 62.5 MPa nor the validated peak sigma_max = 157.44 MPa, so the message should report a wrong Kt or wrong nominal in addition to the missing concentration factor."
  }
}
```

## Reference Solution (independent, in-repo)

```text
d/W = 12/60 = 0.2
s = 1 - d/W = 0.8
Kt_net = 2 + 0.284 s - 0.600 s^2 + 1.32 s^3 = 2.519040
sigma_net = 18000 N / ((60 - 12) mm * 6 mm) = 62.5 MPa
sigma_max = 2.519040 * 62.5 = 157.44 MPa
```

Haiku reported **72.9 MPa** — it omitted `Kt` and computed the nominal on a wrong
net area `(W t - pi(d/2)^2)` instead of `(W - d) t`. The true peak is ~2.16x
higher. MechAudit flags `FM-04`.
