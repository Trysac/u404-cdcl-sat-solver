# CDCL SAT Solver Engine with 2WL, 1-UIP, Luby Restarts, and Incremental Assumptions

Status: accepted (generated, pending human review)

## Context

The SAT solver library requires a complete, deterministic, pure-Python CDCL solver engine implementing two-watched-literals (2WL) unit propagation, 1-UIP conflict analysis, VSIDS heuristics with phase saving, Luby restarts, DRAT proof generation, and incremental assumption-based solving with minimal core extraction.

## Decision

Implement Solver in src/cdcl_engine/engine.py using in-place two-watched-literals updates, 1-UIP conflict analysis with backjumping, lazy max-heap VSIDS variable selection with polarity phase saving, Luby restarts, DRAT UNSAT proof output, and assumption decision-level synchronization with backward implication graph analysis for unsatisfiable core extraction.

## Consequences

Provides a clean, dependency-free, high-performance CDCL solver that supports incremental queries, DRAT proof verification via reverse unit propagation, strict type safety, and 100% test branch coverage.
