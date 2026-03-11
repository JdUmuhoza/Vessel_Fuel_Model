"""Lightweight experiment tracking utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ExperimentTracker:
    """Append-only JSONL tracker for reproducible experiments."""

    out_dir: Path
    run_name: str

    def __post_init__(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.out_dir / f"{self.run_name}.jsonl"

    def log(self, payload: dict[str, Any]) -> None:
        """Append one tracking record."""
        row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
