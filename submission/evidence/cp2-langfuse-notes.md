# CP2 Langfuse evidence notes

Captured during `feat/cp2-observability` implementation. Replace/add screenshots beside these IDs before final submission.

## Prompt versions

- Prompt name: `day13-chat`
- Version 1 labels: `baseline`, `production` (after rollback)
- Version 2 labels: `candidate` (briefly also held `production` during promote test)

Created via:

```bash
python scripts/setup_langfuse_prompts.py
python scripts/setup_langfuse_prompts.py --promote-v2
python scripts/setup_langfuse_prompts.py --rollback-v1
```

## Trace IDs (sample ≥10)

| Trace ID | prompt_label | prompt_version | prompt_source |
|---|---|---|---|
| `470c5f0fe8143baa51cd970f137777ea` | candidate | 2 | langfuse |
| `287116b25ab305c5644fb33002161437` | baseline | 1 | langfuse |
| `bcdbc1a8949ea694ec431b7dfc5852e4` | production | 1 | langfuse |
| `985f218d76f50ea64295bef15454df6e` | production | 1 | langfuse |
| `537aa190afc46a15e99ea37b9fad31af` | production | 1 | langfuse |
| `560b0d9d207e25d31a77fd62ec3eb2e4` | production | 1 | langfuse |
| `f87f4fe13c45fe7f3d51b42d603daddb` | production | 1 | langfuse |
| `1c5df04cf1a801518ff357a2b117c8fb` | production | 1 | langfuse |
| `0d6f1e916b9991703e9b5399432dd489` | production | 1 | langfuse |
| `4b03c0e58437dda862b876c1c3f85fde` | production | 1 | langfuse |
| `e2807d3136d889d8aebb65eed8c3ec63` | production | 1 | langfuse |
| `1681b7a7604930e056dba863bd53e195` | production | 1 | langfuse |

Primary prompt-version comparison pair:

- Baseline: `287116b25ab305c5644fb33002161437` (v1)
- Candidate: `470c5f0fe8143baa51cd970f137777ea` (v2)

## Screenshots still required (manual)

1. Langfuse prompt list showing v1 + v2
2. Waterfall of one trace
3. Before/after production label promote + rollback
4. Streamlit dashboard 6 panels (`streamlit run scripts/dashboard_app.py`)
5. `validate_dashboard.py` output `HỢP LỆ: 6/6 panel`
