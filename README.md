# cdcl-sat-solver

[![PyPI version](https://img.shields.io/pypi/v/trysac-cdcl-sat-solver)](https://pypi.org/project/trysac-cdcl-sat-solver/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-cdcl-sat-solver)](LICENSE)
[![CI](https://github.com/Trysac/u404-cdcl-sat-solver/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u404-cdcl-sat-solver/actions/workflows/ci.yml)

Pure-Python CDCL SAT solver with two-watched-literals, 1-UIP learning, DRAT proofs, and assumptions.

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-cdcl-sat-solver
# or
uv add trysac-cdcl-sat-solver
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import cdcl_sat_solver

# normalize() trims surrounding whitespace and lower-cases the text.
print(cdcl_sat_solver.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    cdcl_sat_solver.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
