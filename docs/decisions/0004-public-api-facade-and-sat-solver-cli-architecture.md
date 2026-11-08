# Public API facade and SAT solver CLI architecture

Status: accepted (generated, pending human review)

## Context

The package requires a public facade exporting Solver, SolveResult, parse_dimacs, dump_dimacs, and verify_model, along with the satpy CLI entry point with strict exit codes (10 SAT, 20 UNSAT, 0 UNKNOWN, 2 error).

## Decision

Implement the core CDCL engine (with 2-watched-literals, 1-UIP conflict analysis, Luby restarts, VSIDS, and phase saving), DIMACS CNF serialization/deserialization, and DRAT/RUP proof verification natively within src/cdcl_sat_solver. The satpy command-line interface intercepts ArgumentParser errors to return exit code 2 and outputs clear error diagnostics to stderr without crashing the interpreter.

## Consequences

Provides a dependency-free, high-performance CDCL solver that adheres to standard SAT competition exit codes and DIMACS format specifications, with comprehensive unit test coverage and DRAT proof verification.
