"""Small deterministic helpers for the Locust runner and its tests."""
from __future__ import annotations

from collections import Counter
from pathlib import Path


def ensure_isolated_database(database_path: str | Path, isolated_root: str | Path, operational_path: str | Path) -> Path:
    """Refuse an absent/outside database path and known application default."""
    db = Path(database_path).resolve(strict=False)
    root = Path(isolated_root).resolve(strict=False)
    operational = Path(operational_path).resolve(strict=False)
    if db == operational or not db.is_relative_to(root) or db == root:
        raise ValueError("Refusing non-isolated banking database path")
    return db


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) * fraction + 0.999999999) - 1)))
    return float(ordered[index])


def observed_distribution(requests: list[dict]) -> dict:
    counts = Counter(item["name"] for item in requests)
    total = sum(counts.values())
    return {
        name: {"count": count, "percentage": (100.0 * count / total if total else 0.0)}
        for name, count in sorted(counts.items())
    }


def is_steady_sample(item: dict, steady_start_epoch: float, steady_end_epoch: float) -> bool:
    return steady_start_epoch <= item["start_time"] < steady_end_epoch


def strict_below(value: float | None, limit: float) -> bool:
    return value is not None and value < limit
