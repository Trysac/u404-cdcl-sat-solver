"""Tests for public cdcl_sat_solver facade API."""

from pathlib import Path

import pytest

from cdcl_sat_solver import (
    DratTracer,
    IProofTracer,
    Solver,
    SolverError,
    SolveResult,
    dump_dimacs,
    main,
    parse_dimacs,
    verify_model,
    verify_rup_proof,
)


def test_public_exports_available() -> None:
    assert callable(main)
    assert callable(parse_dimacs)
    assert callable(dump_dimacs)
    assert callable(verify_model)
    assert callable(verify_rup_proof)
    assert Solver is not None
    assert SolveResult is not None
    assert SolverError is not None
    assert DratTracer is not None
    assert IProofTracer is not None


def test_dimacs_acceptance_parse() -> None:
    # WHEN parse_dimacs is called with 'p cnf 3 2\n1 -2 0\n2 3 0\n' THEN it returns num_vars=3 and clauses=[[1, -2], [2, 3]]
    text = "p cnf 3 2\n1 -2 0\n2 3 0\n"
    num_vars, clauses = parse_dimacs(text)
    assert num_vars == 3
    assert clauses == [[1, -2], [2, 3]]


def test_dimacs_acceptance_max_bytes() -> None:
    # IF parse_dimacs input exceeds max_bytes of 10000000 THEN it raises SolverError with code 'input_too_large'
    oversized = "p cnf 1 0\n" + ("c " + "x" * 100 + "\n") * 100_001
    with pytest.raises(SolverError) as exc_info:
        parse_dimacs(oversized, max_bytes=10_000_000)
    assert exc_info.value.code == "input_too_large"


def test_dimacs_parse_errors() -> None:
    with pytest.raises(SolverError) as exc1:
        parse_dimacs("")
    assert exc1.value.code == "dimacs_parse_error"

    with pytest.raises(SolverError) as exc2:
        parse_dimacs("1 2 0\n")
    assert exc2.value.code == "dimacs_parse_error"

    with pytest.raises(SolverError) as exc3:
        parse_dimacs("p cnf 3\n")
    assert exc3.value.code == "dimacs_parse_error"

    with pytest.raises(SolverError) as exc4:
        parse_dimacs("p cnf a b\n")
    assert exc4.value.code == "dimacs_parse_error"

    with pytest.raises(SolverError) as exc5:
        parse_dimacs("p cnf -1 2\n")
    assert exc5.value.code == "dimacs_parse_error"

    with pytest.raises(SolverError) as exc6:
        parse_dimacs("p cnf 3 2\np cnf 3 2\n")
    assert exc6.value.code == "dimacs_parse_error"

    with pytest.raises(SolverError) as exc7:
        parse_dimacs("p cnf 3 2\n1 invalid 0\n")
    assert exc7.value.code == "dimacs_parse_error"


def test_dump_dimacs_and_roundtrip() -> None:
    clauses = [[1, -2], [2, 3]]
    text = dump_dimacs(3, clauses)
    parsed_vars, parsed_clauses = parse_dimacs(text)
    assert parsed_vars == 3
    assert parsed_clauses == clauses

    with pytest.raises(SolverError) as exc:
        dump_dimacs(-1, clauses)
    assert exc.value.code == "invalid_argument"


def test_verify_model() -> None:
    clauses = [[1, 2], [-1, 2]]
    assert verify_model(clauses, {1: True, 2: True}) is True
    assert verify_model(clauses, {1: False, 2: True}) is True
    assert verify_model(clauses, {1: True, 2: False}) is False
    assert verify_model([], {1: True}) is True
    assert verify_model([[]], {1: True}) is False


def test_solve_unsat_acceptance() -> None:
    # WHEN solve is called on clauses [[1, 2], [-1, 2], [1, -2], [-1, -2]] THEN status is 'UNSAT', model is None, and assumptions_core is []
    solver = Solver(2)
    for c in [[1, 2], [-1, 2], [1, -2], [-1, -2]]:
        solver.add_clause(c)
    res = solver.solve()
    assert res.status == "UNSAT"
    assert res.model is None
    assert res.assumptions_core == []


def test_solve_sat_acceptance() -> None:
    # WHEN solve is called on clauses [[1, 2], [-1, 2]] THEN status is 'SAT' and verify_model(clauses, model) returns True
    clauses = [[1, 2], [-1, 2]]
    solver = Solver(2)
    for c in clauses:
        solver.add_clause(c)
    res = solver.solve()
    assert res.status == "SAT"
    assert res.model is not None
    assert verify_model(clauses, res.model) is True


def test_solve_assumptions_acceptance() -> None:
    # WHEN solve is called with assumptions [1] on clauses [[-1]] THEN status is 'UNSAT' and assumptions_core is [1]
    solver = Solver(1)
    solver.add_clause([-1])
    res = solver.solve(assumptions=[1])
    assert res.status == "UNSAT"
    assert res.assumptions_core == [1]


def test_solve_incremental_acceptance() -> None:
    # WHEN a SAT formula receives an added clause satisfied by its existing model THEN status remains 'SAT' with verify_model returning True
    solver = Solver(2)
    solver.add_clause([1, 2])
    solver.add_clause([-1, 2])
    res1 = solver.solve()
    assert res1.status == "SAT"
    assert res1.model is not None

    # Add clause satisfied by res1.model
    # Clause [2] is satisfied because 2 must be True in any satisfying model of [[1, 2], [-1, 2]]
    solver.add_clause([2])
    res2 = solver.solve()
    assert res2.status == "SAT"
    assert res2.model is not None
    assert verify_model(solver.clauses, res2.model) is True


def test_empty_formula_is_sat() -> None:
    solver = Solver(3)
    res = solver.solve()
    assert res.status == "SAT"
    assert res.model == {1: False, 2: False, 3: False}


def test_empty_clause_is_unsat() -> None:
    solver = Solver(1)
    solver.add_clause([])
    res = solver.solve()
    assert res.status == "UNSAT"


def test_tautology_handling() -> None:
    solver = Solver(2)
    solver.add_clause([1, -1])  # Tautology ignored
    solver.add_clause([1, 1, 2])  # Duplicate literal deduplicated
    res = solver.solve()
    assert res.status == "SAT"
    assert res.model is not None


def test_events_and_restarts() -> None:
    events: list[dict[str, object]] = []
    solver = Solver(4, on_event=events.append)
    # Pigeonhole principle: 4 pigeons into 3 holes (UNSAT, generates conflicts & restarts)
    # Pigeons 1..4, Holes 1..3: var(p, h) = (p-1)*3 + h
    for p in range(1, 5):
        solver.add_clause([(p - 1) * 3 + h for h in range(1, 4)])
    for h in range(1, 4):
        for p1 in range(1, 5):
            for p2 in range(p1 + 1, 5):
                solver.add_clause([-((p1 - 1) * 3 + h), -((p2 - 1) * 3 + h)])

    res = solver.solve()
    assert res.status == "UNSAT"
    assert res.conflicts > 0
    assert len(events) > 0


def test_timeout() -> None:
    solver = Solver(2)
    solver.add_clause([1, 2])
    res = solver.solve(time_limit_sec=0.0)
    assert res.status == "UNKNOWN"
    assert res.model is None


def test_drat_and_rup_proof_acceptance(tmp_path: Path) -> None:
    # WHEN proof_path is provided for an UNSAT problem THEN the emitted DRAT file terminates with '0' as its final non-empty line
    # WHEN an UNSAT formula is solved with proof_path set THEN a reverse-unit-propagation checker in the tests accepts every added clause of the proof up to the empty clause '0'
    d = tmp_path
    proof_file = d / "proof.drat"
    clauses = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    solver = Solver(2)
    for c in clauses:
        solver.add_clause(c)

    res = solver.solve(proof_path=str(proof_file))
    assert res.status == "UNSAT"
    assert proof_file.exists()

    lines = [
        line.strip() for line in proof_file.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert lines[-1] == "0"

    # Acceptance: reverse unit propagation checker accepts proof
    verified = verify_rup_proof(clauses, str(proof_file))
    assert verified is True


def test_verify_rup_proof_limits_and_errors(tmp_path: Path) -> None:
    d = tmp_path
    non_existent = d / "non_existent.drat"
    with pytest.raises(SolverError) as exc_io:
        verify_rup_proof([[1]], str(non_existent))
    assert exc_io.value.code == "proof_io_error"

    large_proof = d / "large.drat"
    large_proof.write_text("0\n" * 500, encoding="utf-8")
    with pytest.raises(SolverError) as exc_size:
        verify_rup_proof([[1]], str(large_proof), max_bytes=10)
    assert exc_size.value.code == "input_too_large"

    invalid_rup = d / "invalid_rup.drat"
    # Clause [3] cannot be derived by RUP from [[1, 2]]
    invalid_rup.write_text("3 0\n0\n", encoding="utf-8")
    assert verify_rup_proof([[1, 2]], str(invalid_rup)) is False

    incomplete_proof = d / "incomplete.drat"
    incomplete_proof.write_text("c a comment only\n", encoding="utf-8")
    assert verify_rup_proof([[1, 2]], str(incomplete_proof)) is False

    # Deletion test
    proof_with_deletion = d / "deletion.drat"
    proof_with_deletion.write_text("d 1 0\n0\n", encoding="utf-8")
    # Cannot verify empty clause when active clauses don't derive it
    assert verify_rup_proof([[1]], str(proof_with_deletion)) is False
