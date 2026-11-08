"""Behavior tests for solver paths the acceptance tests do not reach (manual pass 2026-11-08)."""

import io
import itertools
import random
from typing import Any

from cdcl_sat_solver import DratTracer, Solver


def _pigeonhole(pigeons: int, holes: int) -> list[list[int]]:
    def var(p: int, h: int) -> int:
        return p * holes + h + 1

    clauses = [[var(p, h) for h in range(holes)] for p in range(pigeons)]
    for h in range(holes):
        for p1, p2 in itertools.combinations(range(pigeons), 2):
            clauses.append([-var(p1, h), -var(p2, h)])
    return clauses


def _brute_force_sat(num_vars: int, clauses: list[list[int]]) -> bool:
    for bits in itertools.product([False, True], repeat=num_vars):
        if all(any(bits[abs(lit) - 1] == (lit > 0) for lit in c) for c in clauses):
            return True
    return False


def test_empty_formula_is_sat_with_every_variable_false() -> None:
    result = Solver(3).solve()
    assert result.status == "SAT"
    assert result.model == {1: False, 2: False, 3: False}


def test_pigeonhole_is_unsat_and_reports_conflicts_and_restarts() -> None:
    events: list[dict[str, Any]] = []
    solver = Solver(20, on_event=events.append)
    for clause in _pigeonhole(5, 4):
        solver.add_clause(clause)
    result = solver.solve()
    assert result.status == "UNSAT"
    assert result.conflicts > 0
    assert any(e["type"] == "conflict" for e in events)


def test_assumption_that_contradicts_a_unit_clause_is_the_core() -> None:
    solver = Solver(2)
    solver.add_clause([1])
    solver.add_clause([1, 2])
    result = solver.solve(assumptions=[-1])
    assert result.status == "UNSAT"
    assert result.assumptions_core == [-1]


def test_assumptions_that_propagate_into_a_conflict_return_a_core_of_assumptions() -> None:
    solver = Solver(3)
    solver.add_clause([-1, 3])
    solver.add_clause([-2, -3])
    result = solver.solve(assumptions=[1, 2])
    assert result.status == "UNSAT"
    assert result.assumptions_core
    assert set(result.assumptions_core) <= {1, 2}


def test_time_limit_returns_unknown() -> None:
    ticks = iter(range(1000))
    solver = Solver(20)
    for clause in _pigeonhole(5, 4):
        solver.add_clause(clause)
    result = solver.solve(time_limit_sec=0.5, clock=lambda: float(next(ticks)))
    assert result.status == "UNKNOWN"
    assert result.model is None


def test_solver_agrees_with_brute_force_on_random_formulas() -> None:
    rng = random.Random(404)  # noqa: S311 - deterministic test data, not security
    for _ in range(150):
        num_vars = rng.randint(1, 6)
        clauses = [
            [rng.choice([-1, 1]) * rng.randint(1, num_vars) for _ in range(rng.randint(1, 3))]
            for _ in range(rng.randint(1, 14))
        ]
        solver = Solver(num_vars)
        for clause in clauses:
            solver.add_clause(list(clause))
        result = solver.solve()
        assert (result.status == "SAT") == _brute_force_sat(num_vars, clauses), clauses
        if result.model is not None:
            assert all(any(result.model[abs(lit)] == (lit > 0) for lit in c) for c in clauses)


def test_drat_tracer_on_a_stream_writes_additions_and_deletions_and_ignores_writes_after_close() -> (
    None
):
    stream = io.StringIO()
    tracer = DratTracer(stream)
    tracer.emit_clause([1, -2])
    tracer.emit_deletion([1, -2])
    tracer.emit_clause([])
    tracer.close()
    tracer.emit_clause([3])
    tracer.emit_deletion([3])
    tracer.close()
    assert stream.getvalue() == "1 -2 0\nd 1 -2 0\n0\n"
    assert not stream.closed
