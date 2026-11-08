# Exhaustive Truth-Table Oracle and Property-Based Validation for CDCL Solver

Status: accepted (generated, pending human review)

## Context

SAT solvers employ complex heuristics including 2-watched-literals unit propagation, 1-UIP conflict analysis, non-chronological backtracking, and phase saving. Subtleties in implementation can cause unsound model generation or incomplete search paths. Verification against an unassailable ground truth (brute-force truth-table exploration) is required to ensure 100% correctness.

## Decision

Implement an exhaustive 2^n truth-table oracle in tests/oracle/ to verify verdicts and model validity across 300 seeded 10-variable 3-SAT instances covering the satisfiability phase transition. Supplement with Hypothesis property-based testing and PySAT cross-validation.

## Consequences

Provides mathematical guarantees of solver soundness and completeness on 3-SAT instances, establishes automated regression checks across SAT/UNSAT boundaries, and validates generated models against clause sets without adding runtime dependencies.
