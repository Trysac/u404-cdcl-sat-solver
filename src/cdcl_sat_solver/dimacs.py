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
    """Parse a DIMACS CNF formatted string into variable count and clause list.

    Enforces max_bytes limit and strict format validation.
    """
    raw_bytes = text.encode("utf-8")
    if len(raw_bytes) > max_bytes:
        raise SolverError(
            f"Input size ({len(raw_bytes)} bytes) exceeds maximum limit of {max_bytes} bytes",
            code="input_too_large",
        )

    lines = text.splitlines()
    num_vars: int | None = None
    num_clauses: int | None = None
    clauses: list[list[int]] = []
    current_clause: list[int] = []
    header_found = False

    for line_idx, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("c"):
            continue

        if line.startswith("p"):
            if header_found:
                raise SolverError(
                    f"Duplicate problem header on line {line_idx}",
                    code="dimacs_parse_error",
                )
            tokens = line.split()
            if len(tokens) != 4 or tokens[1] != "cnf":
                raise SolverError(
                    f"Malformed problem header on line {line_idx}: {line[:100]}",
                    code="dimacs_parse_error",
                )
            try:
                num_vars = int(tokens[2])
                num_clauses = int(tokens[3])
            except ValueError as err:
                raise SolverError(
                    f"Header counts must be integers on line {line_idx}",
                    code="dimacs_parse_error",
                ) from err
            if num_vars < 0 or num_clauses < 0:
                raise SolverError(
                    f"Header counts cannot be negative on line {line_idx}",
                    code="dimacs_parse_error",
                )
            header_found = True
            continue

        if not header_found:
            raise SolverError(
                f"Clause encountered before header on line {line_idx}",
                code="dimacs_parse_error",
            )

        for tok in line.split():
            try:
                lit = int(tok)
            except ValueError as err:
                raise SolverError(
                    f"Non-integer token '{tok[:50]}' on line {line_idx}",
                    code="dimacs_parse_error",
                ) from err
            if lit == 0:
                clauses.append(current_clause)
                current_clause = []
            else:
                current_clause.append(lit)

    if current_clause:
        clauses.append(current_clause)

    if not header_found or num_vars is None:
        raise SolverError(
            "Missing DIMACS problem header line 'p cnf ...'", code="dimacs_parse_error"
        )

    return num_vars, clauses


def dump_dimacs(num_vars: int, clauses: list[list[int]]) -> str:
    """Serialize variable count and clauses into a DIMACS CNF formatted string."""
    if num_vars < 0:
        raise SolverError("Number of variables cannot be negative", code="invalid_argument")
    lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        lines.append(" ".join(str(lit) for lit in clause) + " 0")
    return "\n".join(lines) + "\n"


def verify_model(clauses: list[list[int]], model: dict[int, bool]) -> bool:
    """Verify that every clause in clauses is satisfied by the assignment model."""
    for clause in clauses:
        clause_satisfied = False
        for lit in clause:
            var = abs(lit)
            val = model.get(var)
            if val is not None and ((lit > 0 and val) or (lit < 0 and not val)):
                clause_satisfied = True
                break
        if not clause_satisfied:
            return False
    return True
