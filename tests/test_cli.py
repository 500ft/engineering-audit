from __future__ import annotations

from pathlib import Path

import pytest

from mechaudit.cli import main


ROOT = Path(__file__).resolve().parents[1]
CASE_FILE = ROOT / "benchmark" / "synthetic" / "syn-fm07-0001.md"


def test_main_writes_report_to_explicit_output(tmp_path: Path) -> None:
    output = tmp_path / "report.md"

    exit_code = main([str(CASE_FILE), "-o", str(output)])

    assert exit_code == 0
    assert output.exists()
    assert "Audit Report: syn-fm07-0001" in output.read_text(encoding="utf-8")


def test_main_writes_report_to_default_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main([str(CASE_FILE)])

    assert exit_code == 0
    assert (tmp_path / "reports" / "syn-fm07-0001.md").exists()


def test_main_reports_error_for_malformed_case_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    malformed = tmp_path / "no-metadata.md"
    malformed.write_text("# Not a case file\n\nNo JSON metadata block here.\n", encoding="utf-8")

    exit_code = main([str(malformed)])

    assert exit_code == 1
    assert "error:" in capsys.readouterr().err
