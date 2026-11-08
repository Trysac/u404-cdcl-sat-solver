"""CDCL SAT solver interface and result types."""

import time
from collections.abc import Callable
from typing import Any, Literal, NamedTuple


class SolveResult(NamedTuple):
    """Result of a CDCL solve invocation."""

    status: Literal["SAT", "UNSAT", "UNKNOWN"]
    model: dict[int, bool] | None
    assumptions_core: list[int]
    conflicts: int
    decisions: int


class Solver:
    """Pure-Python CDCL SAT solver."""

    def __init__(
        self,
        num_vars: int = 0,
        *,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Initialize the solver with an optional initial variable count and event callback."""
        ...

    def add_clause(self, clause: list[int]) -> None:
        """Add a clause to the solver formula."""
        ...

    def solve(
        self,
        assumptions: list[int] | None = None,
        *,
        time_limit_sec: float | None = None,
        proof_path: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> SolveResult:
        """Solve formula with optional assumptions, timeout, and proof logging."""
        ...
