from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Universe:
    name: str
    tickers: list[str]


def load_universe_file(path: str | Path, name: str | None = None) -> Universe:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Universe file not found: {p}")

    tickers: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tickers.append(line)

    if not tickers:
        raise ValueError(f"Universe file has no tickers: {p}")

    return Universe(name=name or p.stem, tickers=tickers)

