# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add `cdcl_sat_solver` facade exporting `Solver`, `parse_dimacs`, `dump_dimacs`, `verify_model`, and `satpy` CLI entry point.
- Add CDCL SAT solver engine with 2-watched-literals, 1-UIP conflict analysis, Luby restarts, VSIDS heuristic, and assumption core extraction.
- Add cdcl_proof module providing DRAT proof logging and Reverse Unit Propagation verification.
- Initial project structure from the factory utility template.
