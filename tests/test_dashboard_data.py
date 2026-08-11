from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dashboard.data import filter_window, load_logs


def write_jsonl(path: Path, rows: list[dict[str, object]], suffix: str = "") -> None:
    body = "\n".join(json.dumps(row) for row in rows)
    path.write_text(body + suffix, encoding="utf-8")


def test_load_logs_skips_invalid_json_and_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "logs.jsonl"
    write_jsonl(
        path,
        [
            {"ts": "2026-08-11T03:00:00Z", "event": "request_received", "correlation_id": "req-1"},
            {"ts": "not-a-time", "event": "response_sent", "correlation_id": "req-2"},
        ],
        suffix="\n{broken-json}\n",
    )

    result = load_logs(path)

    assert len(result.records) == 1
    assert result.records.iloc[0]["correlation_id"] == "req-1"
    assert result.skipped_lines == 2
    assert result.error is None
    assert str(result.records["ts"].dtype) == "datetime64[ns, UTC]"


def test_load_logs_reports_missing_file(tmp_path: Path) -> None:
    result = load_logs(tmp_path / "missing.jsonl")

    assert result.records.empty
    assert result.skipped_lines == 0
    assert result.error == "Log file not found"


def test_load_logs_skips_non_scalar_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "logs.jsonl"
    write_jsonl(
        path,
        [
            {"ts": {"invalid": "timestamp"}, "event": "request_received"},
            {"ts": ["also-invalid"], "event": "response_sent"},
        ],
    )

    result = load_logs(path)

    assert result.records.empty
    assert result.skipped_lines == 2
    assert result.error is None


def test_filter_window_uses_latest_sixty_minutes() -> None:
    records = pd.DataFrame(
        {
            "ts": pd.to_datetime(
                ["2026-08-11T02:59:59Z", "2026-08-11T03:00:00Z", "2026-08-11T04:00:00Z"],
                utc=True,
            ),
            "event": ["response_sent"] * 3,
        }
    )

    result = filter_window(records, pd.Timestamp("2026-08-11T04:00:00Z"))

    assert result["ts"].tolist() == [
        pd.Timestamp("2026-08-11T03:00:00Z"),
        pd.Timestamp("2026-08-11T04:00:00Z"),
    ]
