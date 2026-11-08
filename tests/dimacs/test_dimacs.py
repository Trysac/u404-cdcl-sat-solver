"""Tests for DIMACS parser and serializer."""

from __future__ import annotations

import pytest

from cdcl_dimacs import SolverError, dump_dimacs, parse_dimacs, verify_model


def test_parse_dimacs_acceptance() -> None:
    # Acceptance literal: 'p cnf 3 2\n1 -2 0\n2 3 0\n'
    text = "p cnf 3 2\n1 -2 0\n2 3 0\n"
    num_vars, clauses = parse_dimacs(text)
    assert num_vars == 3
    assert clauses == [[1, -2], [2, 3]]


def test_parse_dimacs_max_bytes_exceeded() -> None:
    # Acceptance literal: 'input_too_large'
    with pytest.raises(SolverError) as exc_info:
        parse_dimacs("p cnf 1 1\n1 0\n", max_bytes=5)
    assert exc_info.value.code == "input_too_large"


def test_parse_dimacs_default_max_bytes() -> None:
    large_input = "c comment\n" * 1_000_001
    with pytest.raises(SolverError) as exc_info:
        parse_dimacs(large_input, max_bytes=10000000)
    assert exc_info.value.code == "input_too_large"


def test_parse_dimacs_comments_and_formatting() -> None:
    text = """
    c this is a comment
    p cnf 4 3
    1 2 0
    -2 3
    -3 4 0
    """
    num_vars, clauses = parse_dimacs(text)
    assert num_vars == 4
    assert clauses == [[1, 2], [-2, 3, -3, 4]]


def test_parse_dimacs_malformed_lines() -> None:
    with pytest.raises(SolverError) as exc_info:
        parse_dimacs("p invalid")
    assert exc_info.value.code == "malformed_dimacs"

    with pytest.raises(SolverError) as exc_info:
        parse_dimacs("p cnf foo bar")
    assert exc_info.value.code == "malformed_dimacs"

    with pytest.raises(SolverError) as exc_info:
        parse_dimacs("p cnf 3 2\n1 abc 0")
    assert exc_info.value.code == "malformed_dimacs"

    with pytest.raises(SolverError) as exc_info:
        parse_dimacs("p cnf -1 2")
    assert exc_info.value.code == "malformed_dimacs"


def test_parse_dimacs_without_problem_line() -> None:
    text = "1 2 0\n-2 3 0\n"
    num_vars, clauses = parse_dimacs(text)
    assert num_vars == 3
    assert clauses == [[1, 2], [-2, 3]]


def test_dump_dimacs() -> None:
    clauses = [[1, -2], [2, 3]]
    output = dump_dimacs(3, clauses)
    assert output == "p cnf 3 2\n1 -2 0\n2 3 0\n"

    parsed_vars, parsed_clauses = parse_dimacs(output)
    assert parsed_vars == 3
    assert parsed_clauses == clauses


def test_verify_model() -> None:
    clauses = [[1, -2], [2, 3]]
    assert verify_model(clauses, {1: True, 2: False, 3: True}) is True
    assert verify_model(clauses, {1: False, 2: False, 3: False}) is False
    assert verify_model(clauses, {1: True, 2: True, 3: False}) is True
    # Missing variable evaluates as unsatisfied if not covered
    assert verify_model(clauses, {1: False, 2: False}) is False
