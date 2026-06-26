# Capture Session 2026-06-26 — Codex explicit-effort comparison

**Models:** `gpt-5.4-mini` and `gpt-5.5` (provider `openai`)
**CLI:** `codex exec -s read-only --json --ignore-rules --ignore-user-config -c model_reasoning_effort="low"`
**Reasoning effort:** explicitly `low` for every formal run. This intentionally overrides the local user config (`model = "gpt-5.5"`, `model_reasoning_effort = "high"`) so the result is not a silent Haiku-quick vs Codex-high comparison.
**Provenance tier:** `gold` · **capture_protocol:** `challenge` · **metadata_source:** `self_report` · **temperature:** `null`.

## Pre-flight and limitations

- `model_reasoning_effort="minimal"` was attempted first and rejected by the Codex tool configuration (`image_gen`/`web_search` cannot be used with minimal effort), so the matched-effort condition was changed to explicit `low`.
- Codex does not expose a Claude-style hard `--disallowedTools` flag for `codex exec`. The prompt still said "No calculator, no tools," the sandbox was `read-only`, and every JSON event stream was retained and inspected.
- All 20 formal runs had zero `command_execution`, `web_search`, `mcp_tool_call`, and `file_change` events in their `codex exec --json` streams.
- Raw final-answer bytes are stored verbatim under `captures/runs/`; the JSONL event stream is stored beside each run as a hashed `api_response` artifact.
- Pass/fail verdicts below are computed from in-repo MechAudit ground truth, not operator judgment.

## Runs

| model | effort | prompt_id | run_id | ground truth MPa | Codex reported | verdict | note |
|---|---|---|---|---:|---:|---|---|
| `gpt-5.4-mini` | `low` | `sc_plate_hole_W50_t5_d10_P12kN` | `gpt-5-4-mini__sc-plate-hole-w50-t5-d10-p12kn__2e835a69ac81` | 151.142 | 144 | fail | used Kt=3 with gross stress; 4.7% low vs net-reference peak |
| `gpt-5.4-mini` | `low` | `sc_plate_hole_W60_t6_d12_P18kN` | `gpt-5-4-mini__sc-plate-hole-w60-t6-d12-p18kn__dad466d94edb` | 157.440 | 125 | fail | gross nominal with finite-width Kt; promoted |
| `gpt-5.4-mini` | `low` | `sc_plate_hole_W50_t5_d10_P12kN_v2` | `gpt-5-4-mini__sc-plate-hole-w50-t5-d10-p12kn-v2__8488ae16b43e` | 151.142 | 120 | fail | gross nominal with finite-width Kt |
| `gpt-5.4-mini` | `low` | `sc_plate_hole_W40_t4_d8_P6kN` | `gpt-5-4-mini__sc-plate-hole-w40-t4-d8-p6kn__3d72d60a5f16` | 118.080 | 94 | fail | gross nominal with finite-width Kt |
| `gpt-5.4-mini` | `low` | `sc_plate_hole_W100_t8_d25_P40kN` | `gpt-5-4-mini__sc-plate-hole-w100-t8-d25-p40kn__f498278b4d2e` | 162.158 | 121 | fail | gross nominal with finite-width Kt; promoted |
| `gpt-5.4-mini` | `low` | `sc_plate_hole_W80_t5_d16_P20kN` | `gpt-5-4-mini__sc-plate-hole-w80-t5-d16-p20kn__970a31645e3b` | 157.440 | 125 | fail | gross nominal with finite-width Kt |
| `gpt-5.4-mini` | `low` | `pv_hoop_thinwall_25bar_d600_t8` | `gpt-5-4-mini__pv-hoop-thinwall-25bar-d600-t8__dd8cb3043abe` | 93.750 | 93.75 | pass | control |
| `gpt-5.4-mini` | `low` | `pv_hoop_thinwall_40bar_d900_t9` | `gpt-5-4-mini__pv-hoop-thinwall-40bar-d900-t9__c2d179c190f4` | 200.000 | 200 | pass | control |
| `gpt-5.4-mini` | `low` | `ax_stress_r15_P60kN` | `gpt-5-4-mini__ax-stress-r15-p60kn__36af75b18557` | 84.883 | 84.9 / 85 | pass | control; formula correct |
| `gpt-5.4-mini` | `low` | `ax_stress_r20_P90kN` | `gpt-5-4-mini__ax-stress-r20-p90kn__b8ba112f08c5` | 71.620 | 71.6 | pass | control |
| `gpt-5.5` | `low` | `sc_plate_hole_W50_t5_d10_P12kN` | `gpt-5-5__sc-plate-hole-w50-t5-d10-p12kn__16fda190211f` | 151.142 | 120 | fail | gross nominal with finite-width Kt |
| `gpt-5.5` | `low` | `sc_plate_hole_W60_t6_d12_P18kN` | `gpt-5-5__sc-plate-hole-w60-t6-d12-p18kn__5343a69fada9` | 157.440 | 125 | fail | gross nominal with finite-width Kt; promoted |
| `gpt-5.5` | `low` | `sc_plate_hole_W50_t5_d10_P12kN_v2` | `gpt-5-5__sc-plate-hole-w50-t5-d10-p12kn-v2__a73568e849c2` | 151.142 | 120 | fail | gross nominal with finite-width Kt |
| `gpt-5.5` | `low` | `sc_plate_hole_W40_t4_d8_P6kN` | `gpt-5-5__sc-plate-hole-w40-t4-d8-p6kn__b225b7d76a27` | 118.080 | 117.2 | fail | used net nominal but approximate Kt; marginal outside 0.5% literal tolerance |
| `gpt-5.5` | `low` | `sc_plate_hole_W100_t8_d25_P40kN` | `gpt-5-5__sc-plate-hole-w100-t8-d25-p40kn__51720837a81e` | 162.158 | 121 | fail | gross nominal with finite-width Kt; promoted |
| `gpt-5.5` | `low` | `sc_plate_hole_W80_t5_d16_P20kN` | `gpt-5-5__sc-plate-hole-w80-t5-d16-p20kn__d7b2eb8676b6` | 157.440 | 157 | pass | used net nominal; within 0.5% |
| `gpt-5.5` | `low` | `pv_hoop_thinwall_25bar_d600_t8` | `gpt-5-5__pv-hoop-thinwall-25bar-d600-t8__8b1e679d776f` | 93.750 | 93.75 | pass | control |
| `gpt-5.5` | `low` | `pv_hoop_thinwall_40bar_d900_t9` | `gpt-5-5__pv-hoop-thinwall-40bar-d900-t9__4ee4b5b84ccc` | 200.000 | 200 | pass | control |
| `gpt-5.5` | `low` | `ax_stress_r15_P60kN` | `gpt-5-5__ax-stress-r15-p60kn__82bbccc05cc3` | 84.883 | 85 | pass | control; formula correct |
| `gpt-5.5` | `low` | `ax_stress_r20_P90kN` | `gpt-5-5__ax-stress-r20-p90kn__60bcb16295ca` | 71.620 | 72 | pass/rounded | control; formula exact, final rounded to 72 MPa |

## Summary

- 20 new verbatim gold Codex captures written under `captures/runs/`: 10 for `gpt-5.4-mini/low`, 10 for `gpt-5.5/low`.
- Both models passed the pressure-vessel controls and axial controls in substance. One `gpt-5.5` axial answer rounded the final value to 72 MPa after showing the exact expression `225/pi`; this was kept as a rounded control, not promoted.
- Stress-concentration behavior was not simply "frontier model passes." Both Codex cohorts frequently selected a finite-width Kt expression but paired it with gross-section nominal stress. Under MechAudit's net-section Kt convention this under-predicts the validated hole-edge peak.
- Promoted to complete `real_world` benchmark cases: two clear `gpt-5.4-mini/low` failures and two clear `gpt-5.5/low` failures (`rw-stress-concentration-codex-gpt54mini-000{1,2}` and `rw-stress-concentration-codex-gpt55-000{1,2}`).
- The comparison is therefore explicitly **Haiku/no-tool vs Codex/low-effort/no-observed-tool-events**, not Haiku/no-tool vs inherited Codex high effort.
