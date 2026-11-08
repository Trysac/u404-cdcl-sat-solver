"""Truth-table brute-force oracle verification on seeded random 3-SAT formulas."""

import random

try:
    from cdcl_sat_solver import Solver, verify_model
except ImportError:
    from cdcl_dimacs import verify_model  # type: ignore[no-redef]
    from cdcl_engine import Solver  # type: ignore[no-redef]


def brute_force_truth_table_oracle(
    num_vars: int,
    clauses: list[list[int]],
) -> tuple[bool, dict[int, bool] | None]:
    """Exhaustive truth-table evaluation over all 2^num_vars assignments.

    Returns (is_satisfiable, model_or_none).
    """
    for mask in range(1 << num_vars):
        assignment = {var: bool((mask >> (var - 1)) & 1) for var in range(1, num_vars + 1)}
        formula_sat = True
        for clause in clauses:
            clause_sat = False
            for lit in clause:
                var = abs(lit)
                val = assignment[var]
                if (lit > 0 and val) or (lit < 0 and not val):
                    clause_sat = True
                    break
            if not clause_sat:
                formula_sat = False
                break
        if formula_sat:
            return True, assignment
    return False, None


def generate_random_3sat_formula(
    rng: random.Random,
    num_vars: int,
    num_clauses: int,
) -> list[list[int]]:
    """Generate a random 3-SAT formula with 3 distinct variables per clause."""
    clauses: list[list[int]] = []
    for _ in range(num_clauses):
        vars_chosen = rng.sample(range(1, num_vars + 1), 3)
        clause = [v if rng.random() < 0.5 else -v for v in vars_chosen]
        clauses.append(clause)
    return clauses


def test_when_300_seeded_random_3sat_formulas_with_10_variables_are_solved() -> None:
    """WHEN 300 seeded random 3-SAT formulas with 10 variables are solved THEN every verdict equals a brute-force truth-table oracle in the tests and every SAT model satisfies the formula."""
    seed = 20260408
    rng = random.Random(seed)  # noqa: S311 - seeded pseudo-random generator for testing
    total_formulas = 300
    num_vars = 10

    sat_count = 0
    unsat_count = 0

    for i in range(total_formulas):
        # Clause count between 20 and 54 spans the phase transition region (alpha ≈ 4.26)
        num_clauses = 20 + (i % 35)
        clauses = generate_random_3sat_formula(rng, num_vars, num_clauses)

        oracle_is_sat, _oracle_model = brute_force_truth_table_oracle(num_vars, clauses)

        solver = Solver(num_vars=num_vars)
        for clause in clauses:
            solver.add_clause(clause)
        result = solver.solve()

        if oracle_is_sat:
            assert result.status == "SAT", (
                f"Formula {i} with {num_clauses} clauses: expected SAT, got {result.status}"
            )
            assert result.model is not None, f"Formula {i}: SAT result must contain a model"
            assert verify_model(clauses, result.model) is True, (
                f"Formula {i}: model did not satisfy clauses"
            )
            sat_count += 1
        else:
            assert result.status == "UNSAT", (
                f"Formula {i} with {num_clauses} clauses: expected UNSAT, got {result.status}"
            )
            assert result.model is None, f"Formula {i}: UNSAT result model must be None"
            unsat_count += 1

    # Ensure the 300 formulas tested both satisfiable and unsatisfiable problem spaces
    assert sat_count > 0, "Expected at least one SAT formula among 300 instances"
    assert unsat_count > 0, "Expected at least one UNSAT formula among 300 instances"
    assert sat_count + unsat_count == total_formulas
