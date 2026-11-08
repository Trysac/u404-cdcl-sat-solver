"""CDCL SAT solver implementation with 2WL, 1-UIP, VSIDS, and Luby restarts."""

import time
from collections.abc import Callable
from typing import Any, Literal, NamedTuple

from cdcl_sat_solver.dimacs import verify_model
from cdcl_sat_solver.proof import DratTracer, IProofTracer


class SolveResult(NamedTuple):
    """Result of a CDCL solve invocation."""

    status: Literal["SAT", "UNSAT", "UNKNOWN"]
    model: dict[int, bool] | None
    assumptions_core: list[int]
    conflicts: int
    decisions: int


def _luby(i: int) -> int:
    """Return the i-th (1-based) value of the Luby restart sequence."""
    k = 1
    while (1 << k) - 1 < i:
        k += 1
    if (1 << k) - 1 == i:
        return 1 << (k - 1)
    return _luby(i - (1 << (k - 1)) + 1)


class Solver:
    """Pure-Python CDCL SAT solver."""

    def __init__(
        self,
        num_vars: int = 0,
        *,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.num_vars = num_vars
        self.on_event = on_event
        self.clauses: list[list[int]] = []
        self.watches: dict[int, list[int]] = {}
        self.assignment: dict[int, bool] = {}
        self.decision_level: dict[int, int] = {}
        self.reason: dict[int, int | None] = {}
        self.trail: list[int] = []
        self.trail_lim: list[int] = []
        self.activity: dict[int, float] = {}
        self.var_inc = 1.0
        self.var_decay = 0.95
        self.phase: dict[int, bool] = {}
        self.qhead = 0
        self._has_empty_clause = False
        self._last_model: dict[int, bool] | None = None
        self._restart_base = 50

        for v in range(1, num_vars + 1):
            self._ensure_var(v)

    def _ensure_var(self, v: int) -> None:
        if v > self.num_vars:
            self.num_vars = v
        if v not in self.activity:
            self.activity[v] = 0.0
        if v not in self.phase:
            self.phase[v] = False
        if v not in self.watches:
            self.watches[v] = []
        if -v not in self.watches:
            self.watches[-v] = []

    def add_clause(self, clause: list[int]) -> None:
        """Add a clause to the solver formula."""
        for lit in clause:
            self._ensure_var(abs(lit))

        # Deduplicate and check for tautologies
        seen_lits: set[int] = set()
        cleaned: list[int] = []
        for lit in clause:
            if -lit in seen_lits:
                return  # Tautology: always satisfied
            if lit not in seen_lits:
                seen_lits.add(lit)
                cleaned.append(lit)

        if not cleaned:
            self._has_empty_clause = True
            return

        ci = len(self.clauses)
        self.clauses.append(cleaned)
        if len(cleaned) == 1:
            # Unit clause
            self.watches[cleaned[0]].append(ci)
        else:
            self.watches[cleaned[0]].append(ci)
            self.watches[cleaned[1]].append(ci)

    @property
    def current_level(self) -> int:
        return len(self.trail_lim)

    def _lit_val(self, lit: int) -> bool | None:
        v = abs(lit)
        if v not in self.assignment:
            return None
        val = self.assignment[v]
        return val if lit > 0 else not val

    def _enqueue(self, lit: int, reason: int | None = None) -> None:
        v = abs(lit)
        val = lit > 0
        self.assignment[v] = val
        self.decision_level[v] = self.current_level
        self.reason[v] = reason
        self.phase[v] = val
        self.trail.append(lit)

    def _cancel_until(self, level: int) -> None:
        while self.current_level > level:
            limit = self.trail_lim.pop()
            while len(self.trail) > limit:
                lit = self.trail.pop()
                v = abs(lit)
                self.assignment.pop(v, None)
                self.decision_level.pop(v, None)
                self.reason.pop(v, None)
        self.qhead = len(self.trail)

    def _propagate(self) -> int | None:
        """Run 2WL BCP; return conflict clause index or None."""
        while self.qhead < len(self.trail):
            p = self.trail[self.qhead]
            self.qhead += 1
            false_lit = -p

            ws = self.watches[false_lit]
            self.watches[false_lit] = []
            i = 0
            while i < len(ws):
                ci = ws[i]
                c = self.clauses[ci]

                if len(c) == 1:
                    self.watches[false_lit].append(ci)
                    i += 1
                    if self._lit_val(c[0]) is False:
                        self.watches[false_lit].extend(ws[i:])
                        self.qhead = len(self.trail)
                        return ci
                    continue

                if c[1] == false_lit:
                    c[0], c[1] = c[1], c[0]

                other = c[1]
                if self._lit_val(other) is True:
                    self.watches[false_lit].append(ci)
                    i += 1
                    continue

                found_replacement = False
                for k in range(2, len(c)):
                    if self._lit_val(c[k]) is not False:
                        c[0], c[k] = c[k], c[0]
                        self.watches[c[0]].append(ci)
                        found_replacement = True
                        break

                if found_replacement:
                    i += 1
                    continue

                self.watches[false_lit].append(ci)
                i += 1
                val_other = self._lit_val(other)
                if val_other is False:
                    self.watches[false_lit].extend(ws[i:])
                    self.qhead = len(self.trail)
                    return ci
                elif val_other is None:
                    self._enqueue(other, reason=ci)

        return None

    def _bump_var(self, v: int) -> None:
        self.activity[v] = self.activity.get(v, 0.0) + self.var_inc
        if self.activity[v] > 1e100:
            for var in self.activity:
                self.activity[var] *= 1e-100
            self.var_inc *= 1e-100

    def _decay_vars(self) -> None:
        self.var_inc /= self.var_decay

    def _analyze(self, confl_ci: int) -> tuple[list[int], int]:
        seen: set[int] = set()
        learned: list[int] = []
        path_count = 0
        c: list[int] = self.clauses[confl_ci]
        trail_idx = len(self.trail) - 1
        p: int | None = None

        while True:
            for lit in c:
                v = abs(lit)
                if v not in seen and self.decision_level.get(v, 0) > 0:
                    self._bump_var(v)
                    seen.add(v)
                    if self.decision_level[v] == self.current_level:
                        path_count += 1
                    else:
                        learned.append(lit)

            while trail_idx >= 0:
                candidate = abs(self.trail[trail_idx])
                trail_idx -= 1
                if candidate in seen:
                    p = candidate
                    break

            path_count -= 1
            if path_count <= 0:
                break

            if p is None:
                break
            r_ci = self.reason[p]
            if r_ci is None:
                break
            c = self.clauses[r_ci]

        if p is None:
            return [], 0
        p_val = self.assignment[p]
        uip_lit = -p if p_val else p
        learned_clause = [uip_lit, *learned]

        if len(learned_clause) <= 1:
            backtrack_level = 0
        else:
            max_idx = 1
            max_level = self.decision_level[abs(learned_clause[1])]
            for i in range(2, len(learned_clause)):
                lvl = self.decision_level[abs(learned_clause[i])]
                if lvl > max_level:
                    max_level = lvl
                    max_idx = i
            learned_clause[1], learned_clause[max_idx] = learned_clause[max_idx], learned_clause[1]
            backtrack_level = max_level

        return learned_clause, backtrack_level

    def _extract_core(self, confl_ci: int, assumptions: list[int]) -> list[int]:
        assumption_set = set(assumptions)
        seen: set[int] = set()
        core_set: set[int] = set()
        queue = list(self.clauses[confl_ci])

        while queue:
            lit = queue.pop()
            v = abs(lit)
            if v in seen:
                continue
            seen.add(v)
            if -lit in assumption_set:
                core_set.add(-lit)
            elif lit in assumption_set:
                core_set.add(lit)
            r_ci = self.reason.get(v)
            if r_ci is not None and r_ci < len(self.clauses):
                queue.extend(self.clauses[r_ci])

        return [a for a in assumptions if a in core_set]

    def _pick_branch_lit(self) -> int | None:
        best_var: int | None = None
        best_act = -1.0
        for v in range(1, self.num_vars + 1):
            if v not in self.assignment:
                act = self.activity.get(v, 0.0)
                if act > best_act:
                    best_act = act
                    best_var = v
        if best_var is None:
            return None
        saved_phase = self.phase.get(best_var, False)
        return best_var if saved_phase else -best_var

    def solve(
        self,
        assumptions: list[int] | None = None,
        *,
        time_limit_sec: float | None = None,
        proof_path: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> SolveResult:
        """Solve formula with optional assumptions, timeout, and proof logging."""
        start_time = clock()
        tracer: IProofTracer | None = DratTracer(proof_path) if proof_path else None

        if self._has_empty_clause:
            if tracer:
                tracer.emit_clause([])
                tracer.close()
            return SolveResult("UNSAT", None, [], 0, 0)

        if not self.clauses:
            model = {v: False for v in range(1, self.num_vars + 1)}
            self._last_model = model
            if tracer:
                tracer.close()
            return SolveResult("SAT", model, [], 0, 0)

        if (
            not assumptions
            and self._last_model is not None
            and verify_model(self.clauses, self._last_model)
        ):
            if tracer:
                tracer.close()
            return SolveResult("SAT", dict(self._last_model), [], 0, 0)

        self._cancel_until(0)
        # Propagate initial unit clauses at level 0
        for ci, c in enumerate(self.clauses):
            if len(c) == 1:
                val = self._lit_val(c[0])
                if val is False:
                    if tracer:
                        tracer.emit_clause([])
                        tracer.close()
                    return SolveResult("UNSAT", None, [], 0, 0)
                elif val is None:
                    self._enqueue(c[0], reason=ci)

        confl = self._propagate()
        if confl is not None:
            if tracer:
                tracer.emit_clause([])
                tracer.close()
            return SolveResult("UNSAT", None, [], 0, 0)

        active_assumptions = assumptions or []
        for a in active_assumptions:
            self._ensure_var(abs(a))

        # Enqueue assumptions
        for a in active_assumptions:
            val = self._lit_val(a)
            if val is False:
                if tracer:
                    tracer.emit_clause([])
                    tracer.close()
                return SolveResult("UNSAT", None, [a], 0, 0)
            elif val is True:
                continue
            self.trail_lim.append(len(self.trail))
            self._enqueue(a, reason=None)
            confl = self._propagate()
            if confl is not None:
                core = self._extract_core(confl, active_assumptions)
                if tracer:
                    tracer.emit_clause([])
                    tracer.close()
                return SolveResult("UNSAT", None, core if core else [a], 0, 0)

        assumption_level = self.current_level
        conflicts = 0
        decisions = 0
        restart_idx = 1
        restart_limit = _luby(restart_idx) * self._restart_base
        conflicts_since_restart = 0

        while True:
            if time_limit_sec is not None and (clock() - start_time) >= time_limit_sec:
                if tracer:
                    tracer.close()
                return SolveResult("UNKNOWN", None, [], conflicts, decisions)

            confl = self._propagate()
            if confl is not None:
                conflicts += 1
                conflicts_since_restart += 1
                if self.current_level == 0:
                    if tracer:
                        tracer.emit_clause([])
                        tracer.close()
                    return SolveResult("UNSAT", None, [], conflicts, decisions)
                if self.current_level <= assumption_level:
                    core = self._extract_core(confl, active_assumptions)
                    if tracer:
                        tracer.emit_clause([])
                        tracer.close()
                    return SolveResult("UNSAT", None, core, conflicts, decisions)

                learned_clause, backtrack_level = self._analyze(confl)
                if tracer:
                    tracer.emit_clause(learned_clause)
                if self.on_event:
                    self.on_event(
                        {"type": "conflict", "conflicts": conflicts, "clause": learned_clause}
                    )

                self._decay_vars()
                target_level = max(backtrack_level, assumption_level)
                self._cancel_until(target_level)

                ci = len(self.clauses)
                self.clauses.append(learned_clause)
                if len(learned_clause) == 1:
                    self.watches[learned_clause[0]].append(ci)
                    self._enqueue(learned_clause[0], reason=ci)
                else:
                    self.watches[learned_clause[0]].append(ci)
                    self.watches[learned_clause[1]].append(ci)
                    self._enqueue(learned_clause[0], reason=ci)
                continue

            if conflicts_since_restart >= restart_limit:
                restart_idx += 1
                restart_limit = _luby(restart_idx) * self._restart_base
                conflicts_since_restart = 0
                if self.on_event:
                    self.on_event(
                        {"type": "restart", "conflicts": conflicts, "restart_idx": restart_idx}
                    )
                self._cancel_until(assumption_level)
                continue

            next_lit = self._pick_branch_lit()
            if next_lit is None:
                model = {v: self.assignment.get(v, False) for v in range(1, self.num_vars + 1)}
                self._last_model = model
                if tracer:
                    tracer.close()
                return SolveResult("SAT", model, [], conflicts, decisions)

            decisions += 1
            self.trail_lim.append(len(self.trail))
            self._enqueue(next_lit, reason=None)
            if self.on_event:
                self.on_event({"type": "decision", "decisions": decisions, "lit": next_lit})
