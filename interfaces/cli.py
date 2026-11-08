"""Command-line interface entry point for satpy."""


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for satpy solving DIMACS files.

    Exit codes:
      10: SAT
      20: UNSAT
       0: UNKNOWN / timeout
       2: IO, parse, or argument error
    """
    ...
