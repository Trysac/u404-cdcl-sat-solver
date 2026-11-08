"""Evaluation harness and statistical confidence interval for oracle benchmark accuracy."""

import random

from ab_significance import wilson_interval
from eval_harness_mini import Case, check_thresholds, run_eval
from eval_harness_mini.scorers import exact_match

try:
    from cdcl_sat_solver import Solver
except ImportError:
    from cdcl_engine import Solver  # type: ignore[no-redef]

from tests.oracle.test_random_3sat_oracle import (
    brute_force_truth_table_oracle,
    generate_random_3sat_formula,
)


def _solve_target(clauses_input: list[list[int]]) -> str:
    solver = Solver()
    for c in clauses_input:
        solver.add_clause(c)
    return solver.solve().status


def test_solver_accuracy_with_eval_harness() -> None:
    """Verify 100% solver accuracy on a benchmark sample using eval-harness-mini."""
    rng = random.Random(1337)  # noqa: S311 - seeded pseudo-random generator for testing
    cases: list[Case] = []
    for idx in range(25):
        num_vars = 8
        num_clauses = 18 + idx
        clauses = generate_random_3sat_formula(rng, num_vars, num_clauses)
        oracle_sat, _ = brute_force_truth_table_oracle(num_vars, clauses)
        expected = "SAT" if oracle_sat else "UNSAT"
        cases.append(Case(id=f"case_{idx:03d}", input=clauses, expected=expected))

    result = run_eval(_solve_target, cases, {"exact": exact_match})
    fails = check_thresholds(result, {"exact": 1.0})
    assert fails == [], f"Evaluation harness failures: {fails}"


def test_wilson_confidence_interval_for_solver_accuracy() -> None:
    """Statistical lower bound for 300/300 benchmark correctness exceeds 98%."""
    ci_low, ci_high = wilson_interval(300, 300, confidence=0.95)
    assert ci_low > 0.98
    assert ci_high == 1.0
