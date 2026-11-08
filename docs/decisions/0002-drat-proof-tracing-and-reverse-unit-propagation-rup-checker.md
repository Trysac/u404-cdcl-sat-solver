# DRAT Proof Tracing and Reverse Unit Propagation (RUP) Checker

Status: accepted (generated, pending human review)

## Context

SAT solvers emit DRAT (Deletion Resolution Asymmetric Tautology) proof logs for unsatisfiable instances so third-party checkers or automated verification pipelines can certify correctness. The interface requires IProofTracer and a verify_rup_proof function.

## Decision

Implement DratProofTracer conforming to IProofTracer to emit clauses and deletions to file or IO stream. Implement verify_rup_proof which parses DRAT lines, tracks the active clause set, and validates each learned clause against existing clauses using Reverse Unit Propagation (unit propagation after asserting negated literals of the clause).

## Consequences

Proof emission can be attached to any CDCL solver instance. Verification runs in pure Python with strict error handling, byte limits, and full branch coverage without third-party runtime dependencies.
