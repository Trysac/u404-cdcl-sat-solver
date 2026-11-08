"""DIMACS CNF format parsing, serialization, and model verification."""

from __future__ import annotations


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
    encoded_len = len(text.encode("utf-8"))
    if encoded_len > max_bytes:
        raise SolverError(
            f"Input size ({encoded_len} bytes) exceeds limit ({max_bytes} bytes)",
            code="input_too_large",
        )

    num_vars: int | None = None
    num_clauses: int | None = None
    clauses: list[list[int]] = []
    current_clause: list[int] = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("c"):
            continue

        if line.startswith("p"):
            parts = line.split()
            if len(parts) != 4 or parts[1] != "cnf":
                raise SolverError(f"Malformed problem line: '{line}'", code="malformed_dimacs")
            try:
                num_vars = int(parts[2])
                num_clauses = int(parts[3])
            except ValueError as err:
                raise SolverError(
                    f"Invalid integer in problem line: '{line}'", code="malformed_dimacs"
                ) from err
            if num_vars < 0 or num_clauses < 0:
                raise SolverError(
                    "Negative variable or clause count in problem line", code="malformed_dimacs"
                )
            continue

        # Clause tokens
        tokens = line.split()
        for tok in tokens:
            try:
                lit = int(tok)
            except ValueError as err:
                raise SolverError(
                    f"Non-integer literal token: '{tok}'", code="malformed_dimacs"
                ) from err

            if lit == 0:
                clauses.append(current_clause)
                current_clause = []
            else:
                current_clause.append(lit)

    if current_clause:
        clauses.append(current_clause)

    if num_vars is None:
        # If no problem line was provided, infer from max literal
        max_v = 0
        for clause in clauses:
            for lit in clause:
                max_v = max(max_v, abs(lit))
        num_vars = max_v

    return num_vars, clauses


def dump_dimacs(num_vars: int, clauses: list[list[int]]) -> str:
    """Serialize variable count and clauses into a DIMACS CNF formatted string."""
    lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        lines.append(" ".join(str(lit) for lit in clause) + " 0")
    return "\n".join(lines) + "\n"


def verify_model(clauses: list[list[int]], model: dict[int, bool]) -> bool:
    """Verify that every clause in clauses is satisfied by the assignment model."""
    for clause in clauses:
        clause_sat = False
        for lit in clause:
            var = abs(lit)
            if var in model:
                val = model[var]
                if (lit > 0 and val) or (lit < 0 and not val):
                    clause_sat = True
                    break
        if not clause_sat:
            return False
    return True
