"""Executable module entry point for satpy."""

import sys

from cdcl_sat_solver.cli import main

if __name__ == "__main__":
    sys.exit(main())
