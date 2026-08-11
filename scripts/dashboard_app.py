from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DASHBOARD_CONFIG = REPO_ROOT / "config" / "dashboard.yaml"


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_records(path: Path, window_minutes: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _parse_ts(rec.get("ts"))
        if ts is None or ts >= cutoff:
            records.append(rec)
    return records


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (pct / 100) * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    weight = rank - low
    return float(ordered[low] * (1 - weight) + ordered[high] * weight)


def minute_bucket(ts: datetime | None) -> str:
    if ts is None:
        return "unknown"
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def load_thresholds(config_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    panels = payload["dashboard"]["panels"]
    return {panel["id"]: panel for panel in panels}


def main() -> None:
    st.set_page_config(page_title="Day 13 Observability Dashboard", layout="wide")
    contract = yaml.safe_load(DASHBOARD_CONFIG.read_text(encoding="utf-8"))["dashboard"]
    panels = load_thresholds(DASHBOARD_CONFIG)
    window = int(contract.get("time_range_minutes", 60))
    refresh = int(contract.get("refresh_seconds", 30))

    st.title(contract.get("title", "Day 13 AI Observability"))
    st.caption(
        f"Source: `{LOG_PATH.relative_to(REPO_ROOT)}` · "
        f"Time range: last {window} minutes · Refresh target: {refresh}s · "
        "Thresholds from config/dashboard.yaml"
    )

    st.caption(f"Click **Rerun** (or enable fragment refresh) about every {refresh}s.")

    @st.fragment(run_every=timedelta(seconds=refresh))
    def render_panels() -> None:
        records = load_records(LOG_PATH, window)
        if not records:
            st.warning(
                f"No log records in the last {window} minutes at {LOG_PATH}. "
                "Run the API + load test first."
            )
            return

        response_sent = [r for r in records if r.get("event") == "response_sent"]
        request_received = [r for r in records if r.get("event") == "request_received"]
        request_failed = [r for r in records if r.get("event") == "request_failed"]

        latencies = [
            float(r["latency_ms"])
            for r in response_sent
            if isinstance(r.get("latency_ms"), (int, float))
        ]
        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        p99 = percentile(latencies, 99)
        latency_threshold = panels["latency"]["threshold"]["value"]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(panels["latency"]["title"])
            st.metric("P50 (ms)", f"{p50:.0f}" if latencies else "n/a")
            st.metric("P95 (ms)", f"{p95:.0f}" if latencies else "n/a")
            st.metric("P99 (ms)", f"{p99:.0f}" if latencies else "n/a")
            st.caption(f"SLO line: p95 ≤ {latency_threshold} ms")
            st.bar_chart({"percentile": {"P50": p50 or 0, "P95": p95 or 0, "P99": p99 or 0}})

        traffic_by_minute: dict[str, int] = defaultdict(int)
        for rec in request_received:
            traffic_by_minute[minute_bucket(_parse_ts(rec.get("ts")))] += 1
        traffic_count = len(request_received)
        rate = traffic_count / max(window, 1)
        traffic_threshold = panels["traffic"]["threshold"]["value"]

        with col2:
            st.subheader(panels["traffic"]["title"])
            st.metric("Request count", traffic_count)
            st.metric("Requests / minute (avg)", f"{rate:.2f}")
            st.caption(f"SLO line: rate_per_minute ≥ {traffic_threshold}")
            if traffic_by_minute:
                st.line_chart({"requests": dict(sorted(traffic_by_minute.items()))})

        received = len(request_received)
        failed = len(request_failed)
        error_rate = (failed / received * 100) if received else 0.0
        error_breakdown = Counter(
            str(r.get("error_type") or "unknown") for r in request_failed
        )
        error_threshold = panels["errors"]["threshold"]["value"]

        with col3:
            st.subheader(panels["errors"]["title"])
            st.metric("Error rate (%)", f"{error_rate:.2f}")
            st.caption(f"SLO line: error_rate_pct ≤ {error_threshold}")
            if error_breakdown:
                st.bar_chart({"count": dict(error_breakdown)})
            else:
                st.write("No errors in window.")

        cost_by_minute: dict[str, float] = defaultdict(float)
        costs = [
            float(r["cost_usd"])
            for r in response_sent
            if isinstance(r.get("cost_usd"), (int, float))
        ]
        total_cost = sum(costs)
        for rec in response_sent:
            if isinstance(rec.get("cost_usd"), (int, float)):
                cost_by_minute[minute_bucket(_parse_ts(rec.get("ts")))] += float(rec["cost_usd"])
        cost_threshold = panels["cost"]["threshold"]["value"]

        tokens_in = sum(
            int(r["tokens_in"])
            for r in response_sent
            if isinstance(r.get("tokens_in"), (int, float))
        )
        tokens_out = sum(
            int(r["tokens_out"])
            for r in response_sent
            if isinstance(r.get("tokens_out"), (int, float))
        )
        tokens_threshold = panels["tokens"]["threshold"]["value"]

        qualities = [
            float(r["quality_score"])
            for r in response_sent
            if isinstance(r.get("quality_score"), (int, float))
        ]
        mean_quality = sum(qualities) / len(qualities) if qualities else float("nan")
        quality_threshold = panels["quality"]["threshold"]["value"]

        row2 = st.columns(3)
        with row2[0]:
            st.subheader(panels["cost"]["title"])
            st.metric("Total cost (USD)", f"{total_cost:.4f}")
            st.caption(f"SLO line: total ≤ {cost_threshold} USD")
            if cost_by_minute:
                st.line_chart({"cost_usd": dict(sorted(cost_by_minute.items()))})

        with row2[1]:
            st.subheader(panels["tokens"]["title"])
            st.metric("tokens_in", tokens_in)
            st.metric("tokens_out", tokens_out)
            st.caption(f"SLO line: sum_by_field ≤ {tokens_threshold}")
            st.bar_chart({"tokens": {"tokens_in": tokens_in, "tokens_out": tokens_out}})

        with row2[2]:
            st.subheader(panels["quality"]["title"])
            st.metric("Mean quality_score", f"{mean_quality:.3f}" if qualities else "n/a")
            st.caption(f"SLO line: mean ≥ {quality_threshold}")
            quality_by_minute: dict[str, list[float]] = defaultdict(list)
            for rec in response_sent:
                if isinstance(rec.get("quality_score"), (int, float)):
                    quality_by_minute[minute_bucket(_parse_ts(rec.get("ts")))].append(
                        float(rec["quality_score"])
                    )
            if quality_by_minute:
                st.line_chart(
                    {
                        "quality_mean": {
                            minute: sum(vals) / len(vals)
                            for minute, vals in sorted(quality_by_minute.items())
                        }
                    }
                )

    render_panels()


if __name__ == "__main__":
    main()
