from __future__ import annotations

import pytest

from app import logging_config


@pytest.fixture(autouse=True)
def isolate_log_file(tmp_path, monkeypatch):
    """Khong cho test ghi vao data/logs.jsonl that.

    Ly do: agent.py ghi 2 su kien rag_retrieved/llm_generated. Khi test goi
    thang agent.run() (ngoai context mot HTTP request) thi khong co
    correlation_id nao duoc bind, nen ban ghi sinh ra se thieu truong
    correlation_id ma config/logging_schema.json bat buoc phai co.

    Nhung ban ghi rac do lan vao data/logs.jsonl — la nguon du lieu that cua
    dashboard va cua evidence nop bai. Fixture nay tro LOG_PATH sang thu muc
    tam cho moi test, nen chay pytest khong con lam ban log that nua.
    """
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "test-logs.jsonl")
