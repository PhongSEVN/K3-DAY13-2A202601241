from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class LogReadResult:
    records: pd.DataFrame
    skipped_lines: int
    error: str | None = None


def load_logs(path: Path) -> LogReadResult:
    if not path.exists():
        return LogReadResult(pd.DataFrame(), 0, "Log file not found")

    rows: list[dict[str, object]] = []
    skipped = 0
    try:
        with path.open(encoding="utf-8") as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    continue
                try:
                    row = json.loads(raw_line)
                except (json.JSONDecodeError, TypeError):
                    skipped += 1
                    continue
                if not isinstance(row, dict) or "ts" not in row or "event" not in row:
                    skipped += 1
                    continue
                try:
                    parsed_ts = pd.to_datetime(row["ts"], utc=True, errors="coerce")
                except (TypeError, ValueError):
                    skipped += 1
                    continue
                if not isinstance(parsed_ts, pd.Timestamp) or pd.isna(parsed_ts):
                    skipped += 1
                    continue
                row["ts"] = parsed_ts
                rows.append(row)
    except OSError as exc:
        return LogReadResult(pd.DataFrame(), skipped, f"Could not read log file: {exc}")

    records = pd.DataFrame(rows)
    if not records.empty:
        records["ts"] = pd.to_datetime(records["ts"], utc=True)
        records = records.sort_values("ts").reset_index(drop=True)
    return LogReadResult(records, skipped)


def filter_window(
    records: pd.DataFrame,
    now: pd.Timestamp,
    minutes: int = 60,
) -> pd.DataFrame:
    if records.empty or "ts" not in records:
        return records.copy()
    end = pd.Timestamp(now)
    end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
    start = end - pd.Timedelta(minutes=minutes)
    mask = records["ts"].between(start, end, inclusive="both")
    return records.loc[mask].copy().reset_index(drop=True)
