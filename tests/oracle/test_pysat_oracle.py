"""Cross-validation against PySAT reference solver when available."""

import random

import pytest

try:
    from pysat.solvers import Glucose3  # type: ignore[import-untyped]

    HAS_PYSAT = True
except ImportError:
    HAS_PYSAT = False

try:
    from cdcl_sat_solver import Solver, verify_model
except ImportError:
    from cdcl_dimacs import verify_model  # type: ignore[no-redef]
    from cdcl_engine import Solver  # type: ignore[no-redef]

from tests.oracle.test_random_3sat_oracle import generate_random_3sat_formula


@pytest.mark.skipif(not HAS_PYSAT, reason="python-sat is not installed")
def test_cross_validation_against_pysat() -> None:
    """Cross-validate verdicts against PySAT Glucose3 on 30 random formulas."""
    rng = random.Random(999)  # noqa: S311 - seeded pseudo-random generator for testing
    num_vars = 15

    for i in range(30):
        num_clauses = 40 + i
        clauses = generate_random_3sat_formula(rng, num_vars, num_clauses)

        # PySAT solve
        with Glucose3(bootstrap_with=clauses) as pysat_solver:
            pysat_verdict = pysat_solver.solve()

        # Pure-Python CDCL solve
        solver = Solver(num_vars=num_vars)
        for clause in clauses:
            solver.add_clause(clause)
        result = solver.solve()

        if pysat_verdict:
            assert result.status == "SAT"
            assert result.model is not None
            assert verify_model(clauses, result.model) is True
        else:
            assert result.status == "UNSAT"
            assert result.model is None
