"""Assemble snapshots → final JSON universe and write to disk."""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

from sg_dividend_data.models import TickerSnapshot, UniverseEntry
from sg_dividend_data.scoring import score

SGT = timezone(timedelta(hours=8))
SCHEMA_VERSION = 1


def assemble(snapshots: List[TickerSnapshot]) -> dict:
    entries = []
    for snap in snapshots:
        sb = score(snap)
        entry = UniverseEntry.from_snapshot(snap, sb)
        entries.append(entry.model_dump())
    return {
        "generated_at": datetime.now(SGT).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "universe": entries,
    }


def write_universe(snapshots: List[TickerSnapshot], path: Path) -> Path:
    data = assemble(snapshots)
    path = Path(path)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path
