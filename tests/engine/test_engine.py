"""Unit tests for CDCL SAT solver engine."""

from __future__ import annotations

import os
from tempfile import NamedTemporaryFile

import pytest

from cdcl_engine.engine import Solver, SolverError, luby, verify_model
from cdcl_proof import verify_rup_proof


def test_acceptance_unsat_four_clauses() -> None:
    """WHEN solve is called on clauses [[1, 2], [-1, 2], [1, -2], [-1, -2]] THEN status is 'UNSAT', model is None, and assumptions_core is []."""
    solver = Solver()
    clauses = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    for clause in clauses:
        solver.add_clause(clause)
    result = solver.solve()
    assert result.status == "UNSAT"
    assert result.model is None
    assert result.assumptions_core == []


def test_acceptance_sat_two_clauses() -> None:
    """WHEN solve is called on clauses [[1, 2], [-1, 2]] THEN status is 'SAT' and verify_model(clauses, model) returns True."""
    solver = Solver()
    clauses = [[1, 2], [-1, 2]]
    for clause in clauses:
        solver.add_clause(clause)
    result = solver.solve()
    assert result.status == "SAT"
    assert result.model is not None
    assert verify_model(clauses, result.model) is True


def test_acceptance_assumptions_unsat() -> None:
    """WHEN solve is called with assumptions [1] on clauses [[-1]] THEN status is 'UNSAT' and assumptions_core is [1]."""
    solver = Solver()
    clauses = [[-1]]
    for clause in clauses:
        solver.add_clause(clause)
    result = solver.solve(assumptions=[1])
    assert result.status == "UNSAT"
    assert result.assumptions_core == [1]


def test_acceptance_incremental_add_clause_satisfied() -> None:
    """WHEN a SAT formula receives an added clause satisfied by its existing model THEN status remains 'SAT' with verify_model returning True."""
    solver = Solver()
    initial_clauses = [[1, 2], [-1, 2]]
    for clause in initial_clauses:
        solver.add_clause(clause)
    res1 = solver.solve()
    assert res1.status == "SAT"
    assert res1.model is not None
    assert verify_model(initial_clauses, res1.model) is True

    # Pick a clause satisfied by the model
    satisfied_clause = [2, 3]
    solver.add_clause(satisfied_clause)
    res2 = solver.solve()
    assert res2.status == "SAT"
    assert res2.model is not None
    assert verify_model([*initial_clauses, satisfied_clause], res2.model) is True


def test_empty_formula_sat() -> None:
    solver = Solver()
    res = solver.solve()
    assert res.status == "SAT"
    assert res.model is not None
    assert verify_model([], res.model) is True


def test_empty_clause_unsat() -> None:
    solver = Solver()
    solver.add_clause([])
    res = solver.solve()
    assert res.status == "UNSAT"
    assert res.model is None


def test_tautology_and_duplicate_literals() -> None:
    solver = Solver()
    solver.add_clause([1, -1])  # Tautology
    solver.add_clause([2, 2, 3])  # Duplicate literals
    solver.add_clause([-2, 3])
    res = solver.solve()
    assert res.status == "SAT"
    assert res.model is not None
    assert res.model[3] is True


def test_unit_conflict_at_level_zero() -> None:
    solver = Solver()
    solver.add_clause([1])
    solver.add_clause([-1])
    res = solver.solve()
    assert res.status == "UNSAT"
    assert res.model is None
    # Subsequent calls also remain UNSAT
    assert solver.solve().status == "UNSAT"


def test_assumptions_multi_core() -> None:
    solver = Solver()
    solver.add_clause([-1, -2])
    res = solver.solve(assumptions=[1, 2])
    assert res.status == "UNSAT"
    assert res.assumptions_core == [1, 2]


def test_assumptions_subset_in_core() -> None:
    solver = Solver()
    solver.add_clause([-1, -2])
    res = solver.solve(assumptions=[1, 2, 3])
    assert res.status == "UNSAT"
    assert res.assumptions_core == [1, 2]


def test_assumptions_satisfiable() -> None:
    solver = Solver()
    solver.add_clause([1, 2])
    solver.add_clause([-1, 3])
    res = solver.solve(assumptions=[1, 3])
    assert res.status == "SAT"
    assert res.model is not None
    assert res.model[1] is True
    assert res.model[3] is True


def test_contradictory_assumptions() -> None:
    solver = Solver()
    solver.add_clause([1, 2])
    res = solver.solve(assumptions=[1, -1])
    assert res.status == "UNSAT"
    assert res.assumptions_core == [1, -1]


def test_drat_proof_emission_and_rup_verification() -> None:
    # Pigeonhole principle: 3 pigeons in 2 holes
    # Pigeons: 1, 2, 3. Variables: p_{i, j} where i in 1..3, j in 1..2
    # p11=1, p12=2, p21=3, p22=4, p31=5, p32=6
    clauses = [
        [1, 2],
        [3, 4],
        [5, 6],
        [-1, -3],
        [-1, -5],
        [-3, -5],
        [-2, -4],
        [-2, -6],
        [-4, -6],
    ]
    with NamedTemporaryFile(suffix=".drat", delete=False) as tmp:
        proof_path = tmp.name

    try:
        solver = Solver(num_vars=6)
        for c in clauses:
            solver.add_clause(c)
        res = solver.solve(proof_path=proof_path)
        assert res.status == "UNSAT"

        # DRAT file terminates with '0' as final non-empty line
        with open(proof_path, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        assert lines[-1] == "0"

        # Reverse unit propagation verification
        assert verify_rup_proof(clauses, proof_path) is True
    finally:
        if os.path.exists(proof_path):
            os.remove(proof_path)


def test_timeout_and_mock_clock() -> None:
    mock_time = 0.0

    def mock_clock() -> float:
        nonlocal mock_time
        mock_time += 1.0
        return mock_time

    solver = Solver()
    # Construct a non-trivial formula
    for i in range(1, 20):
        solver.add_clause([i, i + 1])
        solver.add_clause([-i, -(i + 1)])
    res = solver.solve(time_limit_sec=0.5, clock=mock_clock)
    assert res.status == "UNKNOWN"
    assert res.model is None


def test_events_callback() -> None:
    events: list[dict[str, object]] = []
    solver = Solver(on_event=lambda e: events.append(e))
    solver.add_clause([1, 2])
    solver.add_clause([-1, 2])
    solver.add_clause([1, -2])
    solver.add_clause([-1, -2])
    res = solver.solve()
    assert res.status == "UNSAT"
    types = {e["type"] for e in events}
    assert "decision" in types or "conflict" in types


def test_luby_sequence() -> None:
    expected = [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]
    assert [luby(i) for i in range(1, 16)] == expected


def test_error_handling() -> None:
    solver = Solver()
    with pytest.raises(SolverError) as exc:
        solver.add_clause("not a list")  # type: ignore[arg-type]
    assert exc.value.code == "invalid_clause"

    with pytest.raises(SolverError) as exc:
        solver.add_clause([0])
    assert exc.value.code == "invalid_clause"

    with pytest.raises(SolverError) as exc:
        solver.add_clause(["bad"])  # type: ignore[list-item]
    assert exc.value.code == "invalid_clause"

    with pytest.raises(SolverError) as exc:
        solver.solve(assumptions=[0])
    assert exc.value.code == "invalid_assumption"

    with pytest.raises(SolverError) as exc:
        solver.solve(time_limit_sec=-1.0)
    assert exc.value.code == "invalid_time_limit"

    with pytest.raises(SolverError) as exc:
        Solver(num_vars=-5)
    assert exc.value.code == "invalid_num_vars"


def test_verify_model_negative() -> None:
    clauses = [[1, 2], [-1, -2]]
    bad_model = {1: True, 2: True}
    assert verify_model(clauses, bad_model) is False
    partial_model = {1: False}
    assert verify_model(clauses, partial_model) is False
