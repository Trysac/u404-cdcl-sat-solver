"""Command-line interface entry point for satpy."""

import argparse
import sys
from typing import NoReturn

from cdcl_sat_solver.dimacs import SolverError, parse_dimacs
from cdcl_sat_solver.solver import Solver


class CliArgumentError(Exception):
    """Raised when CLI argument parsing fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SatpyParser(argparse.ArgumentParser):
    """ArgumentParser that raises CliArgumentError instead of exiting."""

    def error(self, message: str) -> NoReturn:
        raise CliArgumentError(message)

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        raise CliArgumentError(message or f"Parser exited with status {status}")


def _build_parser() -> SatpyParser:
    parser = SatpyParser(
        prog="satpy",
        description="satpy: Pure-Python CDCL SAT solver.",
    )
    parser.add_argument("cnf_file", help="Path to DIMACS CNF file to solve")
    parser.add_argument(
        "--proof",
        "-p",
        dest="proof_path",
        default=None,
        help="Path to emit DRAT proof for UNSAT instances",
    )
    parser.add_argument(
        "--time-limit",
        "-t",
        type=float,
        default=None,
        help="Timeout in seconds",
    )
    parser.add_argument(
        "--assumptions",
        "-a",
        default=None,
        help="Comma-separated list of assumption literals, e.g. 1,-2",
    )
    parser.add_argument(
        "--no-model",
        action="store_true",
        help="Do not print satisfying assignment model",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for satpy solving DIMACS files.

    Exit codes:
      10: SAT
      20: UNSAT
       0: UNKNOWN / timeout
       2: IO, parse, or argument error
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except CliArgumentError as e:
        sys.stderr.write(f"Error: {e.message}\n")
        return 2

    if args.time_limit is not None and args.time_limit < 0:
        sys.stderr.write("Error: --time-limit must be non-negative\n")
        return 2

    assumptions: list[int] = []
    if args.assumptions:
        for item in args.assumptions.split(","):
            cleaned = item.strip()
            if not cleaned:
                continue
            try:
                assumptions.append(int(cleaned))
            except ValueError:
                sys.stderr.write(f"Error: invalid assumption literal '{cleaned}'\n")
                return 2

    try:
        with open(args.cnf_file, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        sys.stderr.write(f"IO error: {e}\n")
        return 2

    try:
        num_vars, clauses = parse_dimacs(text)
    except SolverError as e:
        sys.stderr.write(f"Parse error: {e}\n")
        return 2

    solver = Solver(num_vars)
    for clause in clauses:
        solver.add_clause(clause)

    result = solver.solve(
        assumptions=assumptions if assumptions else None,
        time_limit_sec=args.time_limit,
        proof_path=args.proof_path,
    )

    if result.status == "SAT":
        sys.stdout.write("s SATISFIABLE\n")
        if not args.no_model and result.model is not None:
            model_tokens = [str(var if val else -var) for var, val in sorted(result.model.items())]
            sys.stdout.write(f"v {' '.join(model_tokens)} 0\n")
        return 10
    elif result.status == "UNSAT":
        sys.stdout.write("s UNSATISFIABLE\n")
        return 20
    else:
        sys.stdout.write("s UNKNOWN\n")
        return 0
