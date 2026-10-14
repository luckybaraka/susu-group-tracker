"""Entry point so the tracker can be run with ``python -m susu``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
