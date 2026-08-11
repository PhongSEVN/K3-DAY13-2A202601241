# CP3 Challenge investigation notes

## Challenge config (do not edit `config/challenge.json`)

| Field | Value |
|---|---|
| Challenge ID | `day13-k3-observability-v1` |
| Cohort | `K3` |
| Incident | `rag_slow` |
| Affected feature | `refund` |
| Latency threshold | `2000` ms |
| Seed | `1303` |

## Commands run

```bash
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
# after investigation
python scripts/inject_incident.py --disable
```

## Metrics → Traces → Logs

### 1) Metrics (symptom)

| Window | traffic | latency_p95 | quality_avg | errors |
|---|---|---|---|---|
| Before challenge | 10 | 1391 ms | 0.88 | none |
| After challenge | 15 | **2651 ms** | 0.8733 | none |

- P95 **2651 ms > 2000 ms** threshold → alert class: High Latency P95.
- Error rate unchanged (0%) → not `tool_fail`.
- Cost did not spike 4× → not `cost_spike`.

### 2) Logs (proof)

All five challenge `/chat` responses (feature=`refund`) logged ~2650 ms:

| correlation_id | feature | latency_ms | session_id |
|---|---|---|---|
| `req-434b6fd1` | refund | 2651 | k3-challenge-s01 |
| `req-a53efcfe` | refund | 2651 | k3-challenge-s04 |
| `req-f7410241` | refund | 2651 | k3-challenge-s03 |
| `req-224dab80` | refund | 2650 | k3-challenge-s05 |
| `req-622b55a2` | refund | 2651 | k3-challenge-s02 |

After adding `rag_retrieve` span logging:

- event `rag_retrieve_done` with `latency_ms=2500`, `payload.rag_slow_enabled=true`

### 3) Traces

Open Langfuse traces created during the challenge load (tags include `refund` / session `k3-challenge-*`).  
Representative recent generation traces from the challenge window (verify in UI by time + tag `refund`):

- `f8ff1155b342507b2a5b63adef42b2ea`
- `07102518e4b9bb697111d45481c38b6d`
- `f0048a4d84270a753cbf6d717effe0e9`
- `92d69592a00c1ef712edead1c83ee9b4`
- `3d90edbfa9d114b5553a159d9a41f0c4`

Primary evidence pair for report:

- Correlation ID: `req-434b6fd1`
- Trace ID (open nearest refund/`run` around 2026-08-11 10:33): `f8ff1155b342507b2a5b63adef42b2ea` (confirm metadata/tags in UI)

## Root cause

`incident=rag_slow` enables an artificial delay in `app/mock_rag.py`:

```python
if STATE["rag_slow"]:
    time.sleep(2.5)
```

That alone adds **2500 ms** to retrieve. Plus FakeLLM ~150 ms → total ~**2650 ms**, matching logs/metrics and exceeding the challenge threshold of 2000 ms. Feature `refund` queries always hit retrieve for refund corpus docs.

## Fix action

1. Disable incident after investigation: `python scripts/inject_incident.py --disable`.
2. Observability fix shipped: wrap `retrieve` with `@observe(name="rag_retrieve")` and emit `rag_retrieve_done` log (`latency_ms`, `rag_slow_enabled`) so the slow span is visible in Metrics → Traces → Logs.
3. Operational: keep alert `High Latency P95` + runbook steps (dashboard → slow trace → correlation ID).

## Preventive measure

1. Always emit a dedicated RAG span + structured log for retrieve latency.
2. Alert when P95 > SLO (3000 ms lab / 2000 ms challenge threshold) for 5 minutes.
3. Gate incident injection behind explicit enable/disable; never leave `rag_slow` on in shared demos.
4. Add canary checks on feature=`refund` latency before marking release healthy.

## Screenshots to add (manual)

- Dashboard Latency panel during/after challenge (P95 elevated)
- Langfuse waterfall showing `rag_retrieve` (~2500 ms) under `run`
- Log snippet for `req-434b6fd1` / `rag_retrieve_done`
