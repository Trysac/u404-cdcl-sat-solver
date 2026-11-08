"""Pure-Python CDCL SAT solver and DIMACS toolkit."""

from cdcl_sat_solver.cli import main
from cdcl_sat_solver.dimacs import SolverError, dump_dimacs, parse_dimacs, verify_model
from cdcl_sat_solver.proof import DratTracer, IProofTracer, verify_rup_proof
from cdcl_sat_solver.solver import Solver, SolveResult

__version__ = "0.1.0"


def normalize(text: str) -> str:
    """Normalize input text by stripping leading/trailing whitespace and lowercasing."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned.lower()


__all__ = [
    "DratTracer",
    "IProofTracer",
    "SolveResult",
    "Solver",
    "SolverError",
    "__version__",
    "dump_dimacs",
    "main",
    "normalize",
    "parse_dimacs",
    "verify_model",
    "verify_rup_proof",
]
