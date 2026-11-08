"""Pure-Python CDCL SAT solver implementation."""

from __future__ import annotations

import contextlib
import heapq
import os
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, NamedTuple


class SolverError(Exception):
    """Base exception for solver and DIMACS parsing errors."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message[:200])
        self.code = code


class SolveResult(NamedTuple):
    """Result of a CDCL solve invocation."""

    status: Literal["SAT", "UNSAT", "UNKNOWN"]
    model: dict[int, bool] | None
    assumptions_core: list[int]
    conflicts: int
    decisions: int


def luby(i: int) -> int:
    """Return the i-th term (1-based) of the Luby sequence: 1, 1, 2, 1, 1, 2, 4, ..."""
    k = 1
    while True:
        if i == (1 << k) - 1:
            return 1 << (k - 1)
        if (1 << (k - 1)) - 1 < i < (1 << k) - 1:
            return luby(i - (1 << (k - 1)) + 1)
        k += 1


def verify_model(clauses: list[list[int]], model: dict[int, bool]) -> bool:
    """Verify that every clause in clauses is satisfied by the assignment model."""
    for clause in clauses:
        sat = False
        for lit in clause:
            v = abs(lit)
            val = model.get(v)
            if val is not None:
                if lit > 0 and val is True:
                    sat = True
                    break
                if lit < 0 and val is False:
                    sat = True
                    break
        if not sat:
            return False
    return True


def _validate_proof_path(proof_path: str) -> None:
    """Validate proof_path against directory traversal and dangerous paths."""
    p = Path(proof_path)
    if ".." in p.parts:
        raise SolverError(
            f"Path traversal detected in proof_path: {proof_path}",
            code="invalid_proof_path",
        )
    # Check normalized form as well
    norm = os.path.normpath(proof_path)
    norm_parts = Path(norm).parts
    if ".." in norm_parts:
        raise SolverError(
            f"Path traversal detected in proof_path: {proof_path}",
            code="invalid_proof_path",
        )


class Solver:
    """Pure-Python CDCL SAT solver featuring 2WL, 1-UIP, Luby restarts, and assumptions."""

    def __init__(
        self,
        num_vars: int = 0,
        *,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Initialize the solver with an optional initial variable count and event callback."""
        if num_vars < 0:
            raise SolverError("num_vars must be non-negative", "invalid_num_vars")
        self.on_event = on_event
        self.max_var = 0
        self.clauses: list[list[int]] = []
        self.watches: dict[int, list[list[int]]] = defaultdict(list)
        self.assign: list[int] = [0]
        self.level: list[int] = [-1]
        self.reason: list[list[int] | None] = [None]
        self.trail: list[int] = []
        self.trail_lim: list[int] = []
        self.qhead: int = 0
        self.activity: list[float] = [0.0]
        self.var_inc: float = 1.0
        self.var_decay: float = 0.95
        self.saved_phase: list[int] = [0]
        self.heap: list[tuple[float, int]] = []
        self.ok: bool = True
        self.conflicts: int = 0
        self.decisions: int = 0
        self.restart_count: int = 1
        self.conflicts_since_restart: int = 0
        self.restart_base: int = 100

        if num_vars > 0:
            self._ensure_var(num_vars)

    def _ensure_var(self, v: int) -> None:
        if v <= self.max_var:
            return
        old_max = self.max_var
        self.max_var = v
        needed = v + 1 - len(self.assign)
        if needed > 0:
            self.assign.extend([0] * needed)
            self.level.extend([-1] * needed)
            self.reason.extend([None] * needed)
            self.activity.extend([0.0] * needed)
            self.saved_phase.extend([0] * needed)
        for var in range(old_max + 1, v + 1):
            heapq.heappush(self.heap, (0.0, var))

    def _enqueue(self, lit: int, reason: list[int] | None) -> None:
        var = abs(lit)
        sign = 1 if lit > 0 else -1
        self.assign[var] = sign
        self.level[var] = len(self.trail_lim)
        self.reason[var] = reason
        self.saved_phase[var] = sign
        self.trail.append(lit)

    def _backtrack(self, target_level: int) -> None:
        if len(self.trail_lim) <= target_level:
            return
        split_point = self.trail_lim[target_level]
        del self.trail_lim[target_level:]
        while len(self.trail) > split_point:
            lit = self.trail.pop()
            var = abs(lit)
            self.assign[var] = 0
            self.level[var] = -1
            self.reason[var] = None
            heapq.heappush(self.heap, (-self.activity[var], var))
        self.qhead = len(self.trail)

    def _bump_var_activity(self, var: int) -> None:
        self.activity[var] += self.var_inc
        if self.activity[var] > 1e100:
            for v in range(1, self.max_var + 1):
                self.activity[v] *= 1e-100
            self.var_inc *= 1e-100
        if self.assign[var] == 0:
            heapq.heappush(self.heap, (-self.activity[var], var))

    def _propagate(self) -> list[int] | None:
        while self.qhead < len(self.trail):
            p = self.trail[self.qhead]
            self.qhead += 1
            false_lit = -p
            ws = self.watches[false_lit]
            if not ws:
                continue

            i = 0
            j = 0
            n_ws = len(ws)
            confl: list[int] | None = None

            while i < n_ws:
                clause = ws[i]
                if clause[0] == false_lit:
                    clause[0], clause[1] = clause[1], clause[0]

                first_lit = clause[0]
                val_first = self.assign[first_lit] if first_lit > 0 else -self.assign[-first_lit]
                if val_first == 1:
                    ws[j] = clause
                    j += 1
                    i += 1
                    continue

                found = False
                for k in range(2, len(clause)):
                    lit_k = clause[k]
                    val_k = self.assign[lit_k] if lit_k > 0 else -self.assign[-lit_k]
                    if val_k != -1:
                        clause[1], clause[k] = clause[k], clause[1]
                        self.watches[clause[1]].append(clause)
                        found = True
                        break

                if found:
                    i += 1
                    continue

                ws[j] = clause
                j += 1
                i += 1

                if val_first == -1:
                    confl = clause
                    while i < n_ws:
                        ws[j] = ws[i]
                        j += 1
                        i += 1
                    break
                else:
                    self._enqueue(first_lit, clause)

            del ws[j:]
            if confl is not None:
                return confl
        return None

    def _analyze(self, confl: list[int]) -> tuple[list[int], int]:
        learned: list[int] = []
        seen: set[int] = set()
        path_count = 0
        p: int | None = None
        cur_confl: list[int] | None = confl
        index = len(self.trail) - 1
        current_level = len(self.trail_lim)

        while True:
            if cur_confl is not None:
                for lit in cur_confl:
                    v = abs(lit)
                    if p is not None and v == abs(p):
                        continue
                    if v not in seen:
                        lvl = self.level[v]
                        if lvl > 0:
                            seen.add(v)
                            self._bump_var_activity(v)
                            if lvl >= current_level:
                                path_count += 1
                            else:
                                learned.append(lit)

            while index >= 0:
                p = self.trail[index]
                index -= 1
                if abs(p) in seen:
                    break
            else:
                break

            seen.remove(abs(p))
            path_count -= 1
            if path_count <= 0:
                learned.append(-p)
                break
            cur_confl = self.reason[abs(p)]

        learned[0], learned[-1] = learned[-1], learned[0]
        self.var_inc /= self.var_decay

        if len(learned) <= 1:
            bt_level = 0
        else:
            max_i = 1
            max_lvl = self.level[abs(learned[1])]
            for i in range(2, len(learned)):
                lvl = self.level[abs(learned[i])]
                if lvl > max_lvl:
                    max_lvl = lvl
                    max_i = i
            learned[1], learned[max_i] = learned[max_i], learned[1]
            bt_level = max_lvl

        return learned, bt_level

    def _analyze_final(self, failed_lit: int, assump_list: list[int]) -> list[int]:
        conflict_assumption = -failed_lit
        core_set: set[int] = {conflict_assumption}
        if len(self.trail_lim) == 0:
            return [a for a in assump_list if a in core_set]

        seen: set[int] = {abs(failed_lit)}
        for i in range(len(self.trail) - 1, -1, -1):
            lit = self.trail[i]
            v = abs(lit)
            if v in seen:
                seen.remove(v)
                r = self.reason[v]
                if r is None:
                    if self.level[v] > 0:
                        core_set.add(lit)
                else:
                    for r_lit in r:
                        if self.level[abs(r_lit)] > 0:
                            seen.add(abs(r_lit))

        return [a for a in assump_list if a in core_set]

    def _pick_branch_lit(self) -> int | None:
        while self.heap:
            neg_act, var = heapq.heappop(self.heap)
            if self.assign[var] == 0:
                if -neg_act < self.activity[var]:
                    heapq.heappush(self.heap, (-self.activity[var], var))
                    continue
                phase = self.saved_phase[var]
                if phase == 0:
                    phase = -1
                return var if phase == 1 else -var
        return None

    def add_clause(self, clause: list[int]) -> None:
        """Add a clause to the solver formula."""
        if not isinstance(clause, list):
            raise SolverError("Clause must be a list of integers", "invalid_clause")

        if len(self.trail_lim) > 0:
            self._backtrack(0)

        clean_clause: list[int] = []
        seen_lits: set[int] = set()
        for lit in clause:
            if not isinstance(lit, int) or lit == 0:
                raise SolverError(f"Invalid literal: {lit}", "invalid_clause")
            if lit in seen_lits:
                continue
            if -lit in seen_lits:
                return
            seen_lits.add(lit)
            clean_clause.append(lit)
            self._ensure_var(abs(lit))

        if not self.ok:
            return

        simplified: list[int] = []
        for lit in clean_clause:
            v = abs(lit)
            val = self.assign[v] if lit > 0 else -self.assign[v]
            if val == 1 and self.level[v] == 0:
                return
            if val == -1 and self.level[v] == 0:
                continue
            simplified.append(lit)

        if len(simplified) == 0:
            self.ok = False
            return

        if len(simplified) == 1:
            lit = simplified[0]
            v = abs(lit)
            val = self.assign[v] if lit > 0 else -self.assign[v]
            if val == -1 and self.level[v] == 0:
                self.ok = False
                return
            if val == 0:
                self._enqueue(lit, [lit])
                confl = self._propagate()
                if confl is not None:
                    self.ok = False
            return

        self.clauses.append(simplified)
        self.watches[simplified[0]].append(simplified)
        self.watches[simplified[1]].append(simplified)

    def solve(
        self,
        assumptions: list[int] | None = None,
        *,
        time_limit_sec: float | None = None,
        proof_path: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> SolveResult:
        """Solve formula with optional assumptions, timeout, and proof logging."""
        if time_limit_sec is not None and time_limit_sec < 0:
            raise SolverError("time_limit_sec must be non-negative", "invalid_time_limit")
        if proof_path is not None:
            _validate_proof_path(proof_path)

        assump_list: list[int] = []
        if assumptions is not None:
            for a in assumptions:
                if not isinstance(a, int) or a == 0:
                    raise SolverError(f"Invalid assumption literal: {a}", "invalid_assumption")
                self._ensure_var(abs(a))
                assump_list.append(a)

        self._backtrack(0)
        confl = self._propagate()
        if confl is not None or not self.ok:
            self.ok = False
            if proof_path is not None:
                with open(proof_path, "w", encoding="utf-8") as pf:
                    pf.write("0\n")
            return SolveResult("UNSAT", None, [], self.conflicts, self.decisions)

        start_time = clock()
        restart_limit = luby(self.restart_count) * self.restart_base
        proof_ctx = (
            open(proof_path, "w", encoding="utf-8")  # noqa: SIM115
            if proof_path is not None
            else contextlib.nullcontext(None)
        )

        with proof_ctx as proof_file:
            while True:
                if time_limit_sec is not None and clock() - start_time >= time_limit_sec:
                    self._backtrack(0)
                    return SolveResult("UNKNOWN", None, [], self.conflicts, self.decisions)

                confl = self._propagate()
                if confl is not None:
                    self.conflicts += 1
                    self.conflicts_since_restart += 1
                    if self.on_event is not None:
                        self.on_event({"type": "conflict", "conflicts": self.conflicts})

                    if len(self.trail_lim) == 0:
                        self.ok = False
                        if proof_file is not None:
                            proof_file.write("0\n")
                            proof_file.flush()
                        self._backtrack(0)
                        return SolveResult("UNSAT", None, [], self.conflicts, self.decisions)

                    learned, bt_level = self._analyze(confl)
                    if proof_file is not None:
                        proof_file.write(f"{' '.join(map(str, learned))} 0\n")
                    if self.on_event is not None:
                        self.on_event({"type": "learned", "clause": learned})

                    self.clauses.append(learned)
                    if len(learned) >= 2:
                        self.watches[learned[0]].append(learned)
                        self.watches[learned[1]].append(learned)

                    self._backtrack(bt_level)
                    self._enqueue(learned[0], learned)
                    continue

                if self.conflicts_since_restart >= restart_limit:
                    self.restart_count += 1
                    self.conflicts_since_restart = 0
                    restart_limit = luby(self.restart_count) * self.restart_base
                    if self.on_event is not None:
                        self.on_event({"type": "restart", "conflicts": self.conflicts})
                    self._backtrack(0)
                    continue

                next_lit: int | None = None
                while len(self.trail_lim) < len(assump_list):
                    p_assump = assump_list[len(self.trail_lim)]
                    v = abs(p_assump)
                    val = self.assign[v] if p_assump > 0 else -self.assign[v]
                    if val == -1:
                        core = self._analyze_final(-p_assump, assump_list)
                        if proof_file is not None:
                            proof_file.write("0\n")
                            proof_file.flush()
                        self._backtrack(0)
                        return SolveResult("UNSAT", None, core, self.conflicts, self.decisions)
                    elif val == 1:
                        self.trail_lim.append(len(self.trail))
                        continue
                    else:
                        next_lit = p_assump
                        break

                if next_lit is None and len(self.trail_lim) >= len(assump_list):
                    next_lit = self._pick_branch_lit()
                    if next_lit is None:
                        model = {v: (self.assign[v] == 1) for v in range(1, self.max_var + 1)}
                        self._backtrack(0)
                        return SolveResult("SAT", model, [], self.conflicts, self.decisions)

                self.decisions += 1
                if self.on_event is not None:
                    self.on_event(
                        {
                            "type": "decision",
                            "lit": next_lit,
                            "level": len(self.trail_lim) + 1,
                        }
                    )
                self.trail_lim.append(len(self.trail))
                if next_lit is not None:
                    self._enqueue(next_lit, None)
