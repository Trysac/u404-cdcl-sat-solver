"""Property-based tests comparing CDCL solver results with brute-force truth tables."""

from hypothesis import given, settings
from hypothesis import strategies as st

try:
    from cdcl_sat_solver import Solver, verify_model
except ImportError:
    from cdcl_dimacs import verify_model  # type: ignore[no-redef]
    from cdcl_engine import Solver  # type: ignore[no-redef]

from tests.oracle.test_random_3sat_oracle import brute_force_truth_table_oracle


@st.composite
def cnf_formulas(
    draw: st.DrawFn,
    min_vars: int = 1,
    max_vars: int = 6,
    min_clauses: int = 1,
    max_clauses: int = 15,
) -> tuple[int, list[list[int]]]:
    """Generate random CNF formulas with small variable counts for exhaustive comparison."""
    num_vars = draw(st.integers(min_value=min_vars, max_value=max_vars))
    num_clauses = draw(st.integers(min_value=min_clauses, max_value=max_clauses))
    clauses: list[list[int]] = []
    for _ in range(num_clauses):
        clause_len = draw(st.integers(min_value=1, max_value=min(4, num_vars)))
        vars_chosen = draw(
            st.lists(
                st.integers(min_value=1, max_value=num_vars),
                min_size=clause_len,
                max_size=clause_len,
                unique=True,
            )
        )
        clause = [v if draw(st.booleans()) else -v for v in vars_chosen]
        clauses.append(clause)
    return num_vars, clauses


@settings(max_examples=80, deadline=None)
@given(cnf=cnf_formulas())
def test_solver_matches_oracle_on_random_cnf(cnf: tuple[int, list[list[int]]]) -> None:
    """Property test: Solver status always matches truth-table oracle on arbitrary small CNFs."""
    num_vars, clauses = cnf
    oracle_sat, _ = brute_force_truth_table_oracle(num_vars, clauses)

    solver = Solver(num_vars=num_vars)
    for clause in clauses:
        solver.add_clause(clause)
    result = solver.solve()

    if oracle_sat:
        assert result.status == "SAT"
        assert result.model is not None
        assert verify_model(clauses, result.model) is True
    else:
        assert result.status == "UNSAT"
        assert result.model is None


@settings(max_examples=50, deadline=None)
@given(num_vars=st.integers(min_value=1, max_value=10))
def test_empty_formula_is_satisfiable(num_vars: int) -> None:
    """Property test: Empty clause set is trivially SAT."""
    solver = Solver(num_vars=num_vars)
    result = solver.solve()
    assert result.status == "SAT"
    assert result.model is not None
    assert verify_model([], result.model) is True


@settings(max_examples=50, deadline=None)
@given(num_vars=st.integers(min_value=1, max_value=10))
def test_empty_clause_is_unsatisfiable(num_vars: int) -> None:
    """Property test: Formula containing the empty clause [] is UNSAT."""
    solver = Solver(num_vars=num_vars)
    solver.add_clause([])
    result = solver.solve()
    assert result.status == "UNSAT"
    assert result.model is None
