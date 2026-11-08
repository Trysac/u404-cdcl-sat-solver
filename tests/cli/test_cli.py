"""CLI tests for satpy entry point."""

from pathlib import Path

import pytest

from cdcl_sat_solver import dump_dimacs, verify_rup_proof
from cdcl_sat_solver.cli import main


def test_cli_invalid_arguments_returns_exit_code_2(capsys: pytest.CaptureFixture[str]) -> None:
    # WHEN CLI is invoked with invalid arguments THEN main returns exit code 2 and outputs an error to stderr
    code = main(["--unrecognized-argument"])
    assert code == 2
    captured = capsys.readouterr()
    assert len(captured.err) > 0
    assert "unrecognized" in captured.err.lower() or "error" in captured.err.lower()


def test_cli_missing_positional_args(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([])
    assert code == 2
    captured = capsys.readouterr()
    assert "Error:" in captured.err or "the following arguments are required" in captured.err


def test_cli_negative_time_limit(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    test_file = tmp_path / "f.cnf"
    test_file.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
    code = main(["--time-limit", "-5.0", str(test_file)])
    assert code == 2
    captured = capsys.readouterr()
    assert "--time-limit must be non-negative" in captured.err


def test_cli_invalid_assumptions(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    test_file = tmp_path / "f.cnf"
    test_file.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
    code = main(["-a", "not_an_int", str(test_file)])
    assert code == 2
    captured = capsys.readouterr()
    assert "invalid assumption literal" in captured.err


def test_cli_io_error_nonexistent_file(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["non_existent_sat_file_123456.cnf"])
    assert code == 2
    captured = capsys.readouterr()
    assert "IO error" in captured.err


def test_cli_parse_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.cnf"
    bad_file.write_text("not a valid dimacs content\n", encoding="utf-8")
    code = main([str(bad_file)])
    assert code == 2
    captured = capsys.readouterr()
    assert "Parse error" in captured.err


def test_cli_sat_output(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cnf_file = tmp_path / "sat.cnf"
    cnf_file.write_text("p cnf 3 2\n1 -2 0\n2 3 0\n", encoding="utf-8")
    code = main([str(cnf_file)])
    assert code == 10
    captured = capsys.readouterr()
    assert "s SATISFIABLE" in captured.out
    assert "v " in captured.out
    assert captured.out.strip().endswith("0")


def test_cli_sat_no_model(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cnf_file = tmp_path / "sat_no_model.cnf"
    cnf_file.write_text("p cnf 3 2\n1 -2 0\n2 3 0\n", encoding="utf-8")
    code = main(["--no-model", str(cnf_file)])
    assert code == 10
    captured = capsys.readouterr()
    assert "s SATISFIABLE" in captured.out
    assert "v " not in captured.out


def test_cli_unsat_output(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cnf_file = tmp_path / "unsat.cnf"
    cnf_text = dump_dimacs(2, [[1, 2], [-1, 2], [1, -2], [-1, -2]])
    cnf_file.write_text(cnf_text, encoding="utf-8")
    code = main([str(cnf_file)])
    assert code == 20
    captured = capsys.readouterr()
    assert "s UNSATISFIABLE" in captured.out


def test_cli_unsat_proof_logging(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cnf_file = tmp_path / "unsat_proof.cnf"
    proof_file = tmp_path / "proof.drat"
    clauses = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    cnf_file.write_text(dump_dimacs(2, clauses), encoding="utf-8")

    code = main(["--proof", str(proof_file), str(cnf_file)])
    assert code == 20
    assert proof_file.exists()
    lines = [
        line.strip() for line in proof_file.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert lines[-1] == "0"
    assert verify_rup_proof(clauses, str(proof_file)) is True


def test_cli_timeout(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cnf_file = tmp_path / "timeout.cnf"
    cnf_file.write_text("p cnf 3 2\n1 -2 0\n2 3 0\n", encoding="utf-8")
    code = main(["--time-limit", "0.0", str(cnf_file)])
    assert code == 0
    captured = capsys.readouterr()
    assert "s UNKNOWN" in captured.out


def test_cli_assumptions(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cnf_file = tmp_path / "assumptions.cnf"
    cnf_file.write_text("p cnf 1 1\n-1 0\n", encoding="utf-8")
    code = main(["-a", "1", str(cnf_file)])
    assert code == 20
    captured = capsys.readouterr()
    assert "s UNSATISFIABLE" in captured.out


def test_cli_default_argv(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["satpy", "--invalid-test-flag"])
    code = main()
    assert code == 2
    captured = capsys.readouterr()
    assert len(captured.err) > 0
