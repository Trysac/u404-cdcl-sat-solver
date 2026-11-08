"""DIMACS CNF format parsing, serialization, and model verification."""


class SolverError(Exception):
    """Base exception for solver and DIMACS parsing errors."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def parse_dimacs(
    text: str,
    *,
    max_bytes: int = 10_000_000,
) -> tuple[int, list[list[int]]]:
    """Parse a DIMACS CNF formatted string into variable count and clause list."""
    ...


def dump_dimacs(num_vars: int, clauses: list[list[int]]) -> str:
    """Serialize variable count and clauses into a DIMACS CNF formatted string."""
    ...


def verify_model(clauses: list[list[int]], model: dict[int, bool]) -> bool:
    """Verify that every clause in clauses is satisfied by the assignment model."""
    ...
