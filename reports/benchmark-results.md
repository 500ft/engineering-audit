# MechAudit benchmark eval

| case | verdict | detail |
| --- | --- | --- |
| `rw-pressure-vessel-claude-0001` | PASS | detected == expected: [] |
| `rw-pressure-vessel-claude-0002` | PASS | detected == expected: [] |
| `rw-pressure-vessel-gemini-0001` | PASS | detected == expected: [] |
| `rw-pressure-vessel-gpt-0001` | SKIP | pending_capture |
| `rw-pressure-vessel-gpt-0002` | SKIP | pending_capture |
| `rw-stress-concentration-claude-haiku-0001` | PASS | detected == expected: ['FM-04'] |
| `rw-stress-concentration-claude-haiku-0002` | PASS | detected == expected: ['FM-04'] |
| `rw-stress-concentration-claude-haiku-0003` | PASS | detected == expected: ['FM-04'] |
| `rw-stress-concentration-codex-gpt54mini-0001` | PASS | detected == expected: ['FM-04'] |
| `rw-stress-concentration-codex-gpt54mini-0002` | PASS | detected == expected: ['FM-04'] |
| `rw-stress-concentration-codex-gpt55-0001` | PASS | detected == expected: ['FM-04'] |
| `rw-stress-concentration-codex-gpt55-0002` | PASS | detected == expected: ['FM-04'] |
| `syn-arith-0001` | PASS | detected == expected: ['FM-03'] |
| `syn-cantilever-0001` | PASS | detected == expected: [] |
| `syn-fm01-0001` | PASS | detected == expected: ['FM-01'] |
| `syn-fm02a-0001` | PASS | detected == expected: ['FM-02A'] |
| `syn-fm02b-0001` | PASS | detected == expected: ['FM-02B'] |
| `syn-fm07-0001` | PASS | detected == expected: ['FM-07'] |
| `syn-kt-hole-0001` | PASS | detected == expected: [] |

17 passed, 0 failed, 2 skipped (pass = computed detected modes equal expected modes)
