"""DRAT proof emission and Reverse Unit Propagation (RUP) checking."""

import io
from typing import Protocol

from cdcl_sat_solver.dimacs import SolverError


class IProofTracer(Protocol):
    """Protocol for logging DRAT proofs."""

    def emit_clause(self, clause: list[int]) -> None:
        """Emit a learned clause to the DRAT proof."""
        ...

    def emit_deletion(self, clause: list[int]) -> None:
        """Emit a clause deletion line starting with 'd'."""
        ...

    def close(self) -> None:
        """Finalize and close the proof output stream."""
        ...


class DratTracer:
    """Concrete DRAT proof tracer logging to file or stream."""

    def __init__(self, target: str | io.TextIOBase) -> None:
        if isinstance(target, str):
            self._file: io.TextIOBase = open(target, "w", encoding="utf-8")  # noqa: SIM115
            self._owns_file = True
        else:
            self._file = target
            self._owns_file = False
        self._closed = False

    def emit_clause(self, clause: list[int]) -> None:
        if self._closed:
            return
        if not clause:
            self._file.write("0\n")
        else:
            self._file.write(" ".join(str(lit) for lit in clause) + " 0\n")

    def emit_deletion(self, clause: list[int]) -> None:
        if self._closed:
            return
        self._file.write("d " + " ".join(str(lit) for lit in clause) + " 0\n")

    def close(self) -> None:
        if not self._closed:
            self._file.flush()
            if self._owns_file:
                self._file.close()
            self._closed = True


def _rup_conflict_check(clauses: list[list[int]], clause: list[int]) -> bool:
    """Check if negating clause and unit propagating over clauses produces a conflict."""
    assignments: dict[int, bool] = {}
    for lit in clause:
        var = abs(lit)
        expected_val = lit < 0  # negate literal
        if var in assignments and assignments[var] != expected_val:
            return True  # tautology negation contains immediate contradiction
        assignments[var] = expected_val

    queue = [lit for lit in clause]
    # Initial conflict check
    for c in clauses:
        if not c:
            return True

    changed = True
    while changed:
        changed = False
        for c in clauses:
            sat = False
            unassigned_lit: int | None = None
            unassigned_count = 0
            false_count = 0

            for lit in c:
                var = abs(lit)
                if var in assignments:
                    val = assignments[var]
                    if (lit > 0 and val) or (lit < 0 and not val):
                        sat = True
                        break
                    else:
                        false_count += 1
                else:
                    unassigned_count += 1
                    unassigned_lit = lit

            if sat:
                continue
            if false_count == len(c):
                return True
            if unassigned_count == 1 and false_count == len(c) - 1 and unassigned_lit is not None:
                u_var = abs(unassigned_lit)
                u_val = unassigned_lit > 0
                if u_var in assignments:
                    if assignments[u_var] != u_val:
                        return True
                else:
                    assignments[u_var] = u_val
                    queue.append(unassigned_lit)
                    changed = True
    return False


def verify_rup_proof(
    clauses: list[list[int]],
    proof_path: str,
    *,
    max_bytes: int = 50_000_000,
) -> bool:
    """Verify that a DRAT proof on clauses is accepted by reverse unit propagation."""
    try:
        with open(proof_path, encoding="utf-8") as f:
            content = f.read(max_bytes + 1)
    except OSError as e:
        raise SolverError(f"Cannot open proof file: {e}", code="proof_io_error") from e

    if len(content.encode("utf-8")) > max_bytes:
        raise SolverError(f"Proof file exceeds limit of {max_bytes} bytes", code="input_too_large")

    active_clauses: list[list[int]] = [list(c) for c in clauses]
    empty_clause_verified = False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("c"):
            continue

        if line.startswith("d"):
            tokens = line[1:].strip().split()
            del_clause = [int(t) for t in tokens if int(t) != 0]
            del_set = set(del_clause)
            for i, ac in enumerate(active_clauses):
                if set(ac) == del_set and len(ac) == len(del_clause):
                    del active_clauses[i]
                    break
            continue

        tokens = line.split()
        clause = [int(t) for t in tokens if int(t) != 0]
        if not _rup_conflict_check(active_clauses, clause):
            return False

        active_clauses.append(clause)
        if len(clause) == 0:
            empty_clause_verified = True
            break

    return empty_clause_verified
