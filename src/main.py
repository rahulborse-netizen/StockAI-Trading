"""
Entry point.

Prefer using the CLI:
  python -m src.cli research --ticker RELIANCE.NS --start 2020-01-01 --end 2025-01-01
"""

from src.cli import main


if __name__ == "__main__":
    raise SystemExit(main())