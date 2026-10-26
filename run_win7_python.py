"""Source launcher; deliberately uses installed Python, never the frozen EXE."""
from jat_design.win7_python import main

if __name__ == '__main__':
    raise SystemExit(main())
