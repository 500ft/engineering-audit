from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    message: str
    detected_failure_mode: str | None = None


@dataclass
class AuditResult:
    case_id: str
    source_path: Path
    expected_failure_modes: list[str]
    status: str = "complete"
    skipped: bool = False
    skip_reason: str | None = None
    checks: list[CheckResult] = field(default_factory=list)
    recomputed_values: dict[str, float | str] = field(default_factory=dict)

    @property
    def detected_failure_modes(self) -> list[str]:
        modes = [
            check.detected_failure_mode
            for check in self.checks
            if check.detected_failure_mode is not None
        ]
        return sorted(set(modes))

    @property
    def passed(self) -> bool:
        if self.skipped:
            return True
        return set(self.detected_failure_modes) == set(self.expected_failure_modes)

    def add_check(
        self,
        name: str,
        passed: bool,
        message: str,
        detected_failure_mode: str | None = None,
    ) -> None:
        self.checks.append(
            CheckResult(
                name=name,
                passed=passed,
                message=message,
                detected_failure_mode=detected_failure_mode,
            )
        )
