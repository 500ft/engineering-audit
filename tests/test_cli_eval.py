"""Tests for the `mechaudit eval` batch command (the CI regression gate)."""

from __future__ import annotations

from pathlib import Path

from mechaudit.cli import main

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = REPO_ROOT / "benchmark"


def test_eval_full_benchmark_passes(capsys):
    rc = main(["eval", str(BENCHMARK)])
    out = capsys.readouterr().out
    assert rc == 0
    assert " 0 failed" in out or "0 failed" in out
    # pending capture slots are skipped, not failed
    assert "SKIP" in out and "pending_capture" in out


def test_eval_counts_every_committed_case(capsys):
    main(["eval", str(BENCHMARK)])
    out = capsys.readouterr().out
    n_case_files = len([
        p for p in BENCHMARK.rglob("*.md")
        if p.name.lower() not in {"readme.md", "template.md"}
    ])
    verdicts = [ln for ln in out.splitlines()
                if "  PASS" in ln or "  FAIL" in ln or "  SKIP" in ln or "  ERROR" in ln]
    assert len(verdicts) == n_case_files


def test_eval_writes_report(tmp_path, capsys):
    report = tmp_path / "eval_report.md"
    rc = main(["eval", str(BENCHMARK / "synthetic"), "--report", str(report)])
    capsys.readouterr()
    assert rc == 0
    text = report.read_text(encoding="utf-8")
    assert "| case | verdict | detail |" in text
    assert "syn-fm01-0001" in text


def test_eval_fails_on_regression(tmp_path, capsys):
    # A doctored case that claims a failure mode the (correct) output cannot
    # trigger must FAIL the gate and drive a nonzero exit code.
    src = (BENCHMARK / "synthetic" / "syn-cantilever-0001.md").read_text(encoding="utf-8")
    doctored = src.replace('"failure_modes": []', '"failure_modes": ["FM-01"]', 1)
    assert doctored != src, "fixture assumption broken: expected empty failure_modes"
    case_dir = tmp_path / "cases"
    case_dir.mkdir()
    (case_dir / "doctored.md").write_text(doctored, encoding="utf-8")
    rc = main(["eval", str(case_dir)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAIL" in out


def test_eval_rejects_missing_directory(capsys):
    rc = main(["eval", str(REPO_ROOT / "no_such_dir")])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not a directory" in err
