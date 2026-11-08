"""DRAT proof emission and Reverse Unit Propagation (RUP) checking."""

from typing import Protocol


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


def verify_rup_proof(
    clauses: list[list[int]],
    proof_path: str,
) -> bool:
    """Verify that a DRAT proof on clauses is accepted by reverse unit propagation."""
    ...
