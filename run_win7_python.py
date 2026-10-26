"""Installed Python source entry, always load this extracted copy first."""
from pathlib import Path
import sys

# Also works with a controlled/embedded test interpreter: never import another checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from jat_design.win7_python import main

if __name__ == '__main__':
    raise SystemExit(main())
