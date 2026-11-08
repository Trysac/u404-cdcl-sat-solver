"""DRAT proof logging and Reverse Unit Propagation (RUP) verification."""

from __future__ import annotations

import os
from collections import defaultdict, deque
from collections.abc import Sequence
from typing import IO, Protocol


class ProofError(Exception):
    """Base exception for proof operations and verification errors."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


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


class DratProofTracer:
    """DRAT proof logger writing to a file or stream."""

    def __init__(self, target: str | IO[str]) -> None:
        self._owns_file = False
        self._closed = False
        self._file: IO[str]

        if isinstance(target, str):
            # Explicitly opened and managed via close() or context manager
            self._file = open(target, "w", encoding="utf-8")  # noqa: SIM115
            self._owns_file = True
        else:
            self._file = target

    def emit_clause(self, clause: list[int]) -> None:
        """Emit a learned clause to the DRAT proof."""
        if self._closed:
            raise ProofError("Proof tracer is closed", code="tracer_closed")
        line = " ".join(str(lit) for lit in clause) + " 0\n" if clause else "0\n"
        self._file.write(line)
        self._file.flush()

    def emit_deletion(self, clause: list[int]) -> None:
        """Emit a clause deletion line starting with 'd'."""
        if self._closed:
            raise ProofError("Proof tracer is closed", code="tracer_closed")
        line = "d " + " ".join(str(lit) for lit in clause) + " 0\n" if clause else "d 0\n"
        self._file.write(line)
        self._file.flush()

    def close(self) -> None:
        """Finalize and close the proof output stream."""
        if not self._closed:
            self._closed = True
            self._file.flush()
            if self._owns_file:
                self._file.close()

    def __enter__(self) -> DratProofTracer:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()


def _normalize_clause(clause: Sequence[int]) -> tuple[int, ...] | None:
    """Normalize clause by removing duplicate literals. Returns None if tautological."""
    seen: set[int] = set()
    for lit in clause:
        if -lit in seen:
            return None
        seen.add(lit)
    return tuple(sorted(seen, key=abs))


def _rup_check(
    clause: tuple[int, ...],
    active_clauses: list[tuple[int, ...]],
    max_steps: int = 1_000_000,
) -> bool:
    """Check if `clause` is implied by active_clauses using Reverse Unit Propagation (RUP).

    Assign negations of all literals in clause, then perform unit propagation.
    If contradiction is found, RUP holds.
    """
    # If clause contains opposite literals, it's a tautology
    # If negating clause causes an immediate contradiction:
    neg_literals = {-lit for lit in clause}
    if len(neg_literals) < len(clause):
        # Tautology clause (contains lit and -lit)
        return True

    # State: lit -> bool (1 for True, -1 for False, 0 for unset)
    assigned: dict[int, int] = {}
    trail: deque[int] = deque()

    def assign(lit: int) -> bool:
        # Returns False if conflict occurs
        val = assigned.get(lit, 0)
        if val == 1:
            return True
        if val == -1:
            return False
        assigned[lit] = 1
        assigned[-lit] = -1
        trail.append(lit)
        return True

    # Assume negation of clause: each -lit must be True
    for lit in clause:
        if not assign(-lit):
            return True  # Immediate conflict

    # Check if formula already contains an unsatisfied clause under assigned
    for c in active_clauses:
        # Check if all literals in c are false under assigned
        is_sat = False
        all_false = True
        for lit in c:
            val = assigned.get(lit, 0)
            if val == 1:
                is_sat = True
                break
            if val != -1:
                all_false = False
        if not is_sat and (all_false or len(c) == 0):
            return True

    # Find initial unit clauses among active_clauses under initial assignment
    for c in active_clauses:
        is_sat = False
        unassigned_lit = 0
        unassigned_count = 0
        for lit in c:
            val = assigned.get(lit, 0)
            if val == 1:
                is_sat = True
                break
            if val == 0:
                unassigned_count += 1
                unassigned_lit = lit
        if not is_sat and unassigned_count == 1 and not assign(unassigned_lit):
            return True

    # Index active clauses by literal for fast propagation
    # We watch all occurrences of negative literals
    lit_to_clauses: dict[int, list[int]] = defaultdict(list)
    for c_idx, c in enumerate(active_clauses):
        for lit in c:
            lit_to_clauses[-lit].append(c_idx)

    steps = 0
    while trail:
        steps += 1
        if steps > max_steps:
            return False

        p = trail.popleft()
        # p is True, so -p is False. Check clauses containing -p
        for c_idx in lit_to_clauses.get(p, []):
            c = active_clauses[c_idx]
            # Evaluate clause c under current assignments
            is_sat = False
            unassigned_lit = 0
            unassigned_count = 0
            for lit in c:
                val = assigned.get(lit, 0)
                if val == 1:
                    is_sat = True
                    break
                elif val == 0:
                    unassigned_count += 1
                    unassigned_lit = lit

            if is_sat:
                continue

            if unassigned_count == 0:
                # Conflict: all literals in c are false
                return True
            if unassigned_count == 1 and not assign(unassigned_lit):
                return True

    return False


def verify_rup_proof(
    clauses: list[list[int]],
    proof_path: str,
    *,
    max_bytes: int = 50_000_000,
) -> bool:
    """Verify that a DRAT proof on clauses is accepted by reverse unit propagation.

    Returns True if every added clause is accepted by RUP and proof ends with empty clause 0.
    Returns False otherwise.
    """
    if not os.path.exists(proof_path):
        return False

    try:
        file_size = os.path.getsize(proof_path)
        if file_size > max_bytes:
            raise ProofError(
                f"Proof file size {file_size} exceeds {max_bytes} limit", code="proof_too_large"
            )

        with open(proof_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except ProofError:
        raise
    except OSError:
        return False

    # Prepare initial active clauses
    active_clause_set: set[tuple[int, ...]] = set()
    for c in clauses:
        norm = _normalize_clause(c)
        if norm is not None:
            active_clause_set.add(norm)

    # If the formula already contains an empty clause:
    if () in active_clause_set:
        return True

    empty_clause_derived = False

    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("c"):
            continue

        parts = line_str.split()
        is_deletion = parts[0] == "d"
        tokens = parts[1:] if is_deletion else parts

        if not tokens or tokens[-1] != "0":
            return False

        try:
            lits = [int(tok) for tok in tokens[:-1]]
        except ValueError:
            return False

        norm_c = _normalize_clause(lits)
        if norm_c is None:
            # Tautological clause
            continue

        if is_deletion:
            active_clause_set.discard(norm_c)
        else:
            # Check RUP for norm_c against active_clause_set
            active_list = list(active_clause_set)
            if norm_c != () and not _rup_check(norm_c, active_list):
                return False
            if norm_c == ():
                # Empty clause check
                if () not in active_clause_set and not _rup_check((), active_list):
                    return False
                empty_clause_derived = True
                break
            active_clause_set.add(norm_c)

    return empty_clause_derived
