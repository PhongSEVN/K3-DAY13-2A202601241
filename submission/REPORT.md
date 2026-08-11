# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:
  | Vai | Thành viên | MSSV |
  |---|---|---|
  | A — API & Middleware | Lê Thị Yến Nhi | 2A202601031 |
  | B — Security (PII) | Nguyễn Văn Phong | 2A202601241 |
  | C — Metrics & Dashboard | Nguyễn Thanh Phúc | 2A202601345 |
  | D — SRE & Alerts | Vũ Huy Hoàng | 2A202601057 |
  | E — QA & Lead điều tra | Phạm Khánh Linh | 2A202601507 |

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — xem [evidence/cp0-baseline-validate-logs.txt](evidence/cp0-baseline-validate-logs.txt)
- Tổng số traces: **87** trên Langfuse Cloud (yêu cầu tối thiểu 10) — xem [evidence/cp2-traces-list.json](evidence/cp2-traces-list.json)
- Số PII leak còn lại: **0** (`Potential PII leaks detected: 0`)
- Link/đường dẫn dashboard: _(C — Thanh Phúc điền)_

## 3. Logging và tracing

- Evidence correlation ID: [evidence/cp1-correlation-id-logs.jsonl](evidence/cp1-correlation-id-logs.jsonl) — mỗi bản ghi `service=api` có `correlation_id` dạng `req-<8 hex>`, kèm `user_id_hash`, `session_id`, `feature`, `model`, `env`.
- Evidence PII redaction: [evidence/cp1-pii-redacted-logs.jsonl](evidence/cp1-pii-redacted-logs.jsonl) — email/SĐT/thẻ trong input đã thành `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`.
- Evidence trace waterfall: [evidence/cp3-trace-waterfall.json](evidence/cp3-trace-waterfall.json)
- Giải thích một span đáng chú ý:

  Trace `26c1bec9d203747a6199dd2df08a0d48` có 3 span:

  | Span | Loại | Latency |
  |---|---|---|
  | `run` | GENERATION | 2.655s |
  | `rag-retrieve` | SPAN | **2.501s** |
  | `llm-generate` | SPAN | 0.151s |

  Span `rag-retrieve` chiếm 94% tổng thời gian. Ban đầu repo chỉ sinh đúng một span `run` cho cả request nên không thể biết thời gian nằm ở bước nào; nhóm E đã tách thành span con để trace chỉ đúng được bước lỗi (xem `app/agent.py` và `child_span()` trong `app/tracing.py`).

## 4. Prompt versioning

- Prompt name: `day13-chat` (Langfuse Cloud) — xem [evidence/cp2-prompt-versions.json](evidence/cp2-prompt-versions.json)
- Version/label baseline: **version 1**, labels `baseline` + `production`
  `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\nAnswer briefly in 2-3 sentences.`
- Version/label candidate: **version 2**, labels `candidate` + `latest`
  `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\nAnswer in a short bullet list (max 4 bullets).`
- Trace ID của mỗi version (chạy cùng một input `"What is your refund policy?"`):

  | Label | Version | Session | Trace ID |
  |---|---|---|---|
  | `baseline` | 1 | `s_ab_baseline` | `301ea5b0f276d0f1c985561873459f04` |
  | `candidate` | 2 | `s_ab_candidate` | `388d20e1146e5715891bdf36ac5b5d77` |

  Cả hai trace đều có `prompt_source=langfuse` (không phải fallback local).

- Bằng chứng đổi label hoặc rollback: [evidence/cp2-prompt-rollback.json](evidence/cp2-prompt-rollback.json)

  | Bước | Label v1 | Label v2 | Trace sinh ra |
  |---|---|---|---|
  | Ban đầu | `baseline`, `production` | `candidate`, `latest` | — |
  | Promote v2 | `baseline` | `candidate`, `latest`, `production` | `f48d1f9fe613bf51e80f247de1833126` → ghi `prompt_version=2` |
  | Rollback v1 | `baseline`, `production` | `candidate`, `latest` | `56118dfc5b0c8b787a21cee2bd1b4976` → ghi `prompt_version=1` |

  Hai trace này chứng minh việc đổi label có tác dụng thật lên runtime, không chỉ là thao tác trên UI.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Evidence dashboard: _(C — Thanh Phúc điền)_
- SLO đã chọn và lý do: _(D — Huy Hoàng điền)_
- Alert rules và runbook: _(D — Huy Hoàng điền)_

  Đề xuất từ điều tra CP3 để D cân nhắc: ngưỡng cảnh báo latency nên **chặt hơn** SLO. Sự cố challenge đẩy p95 lên 2656ms — vượt ngưỡng challenge 2000ms nhưng vẫn dưới SLO 3000ms, nên nếu chỉ alert theo SLO thì sự cố này lọt lưới hoàn toàn.

## 6. Điều tra challenge

Bằng chứng đầy đủ: [evidence/cp3-metrics-before-after.txt](evidence/cp3-metrics-before-after.txt), [evidence/cp3-challenge-logs.jsonl](evidence/cp3-challenge-logs.jsonl), [evidence/cp3-trace-waterfall.json](evidence/cp3-trace-waterfall.json)

- **Challenge ID:** `day13-k3-observability-v1` (cohort K3, `affected_feature=refund`, `latency_threshold_ms=2000`)

- **Triệu chứng từ metrics:**
  `latency_p95` tăng từ **1085ms → 2656ms** (2.45 lần), vượt ngưỡng challenge 2000ms.
  `latency_p50` giữ nguyên 155ms → chỉ một nhóm request bị ảnh hưởng, khớp `affected_feature=refund`.
  `error_rate = 0`, token và cost không đổi → loại trừ lỗi LLM và cost spike.

- **Trace ID liên quan:** `26c1bec9d203747a6199dd2df08a0d48` (và 4 trace còn lại: `29fb0491cbca897f1daf5148856badc1`, `c8f8597dc6a6dd7febdeb9d6ad79f766`, `06a08e6d1a3ac55e68c194c5cb5adbd7`, `d5b69cd282f850cdad9a9336a0ed9e66`)
  Span `rag-retrieve` = **2.501s** trong khi `llm-generate` = 0.151s → 94% thời gian nằm ở bước RAG.

- **Log line/correlation ID liên quan:** `req-1dff757e`, `req-ec65a74f`, `req-a0d3940e`, `req-ee3ddb27`, `req-07c6efd7`

  ```
  req-1dff757e | rag_retrieved | latency_ms=2501
  req-1dff757e | llm_generated | latency_ms=150
  req-1dff757e | response_sent | latency_ms=2654
  ```

  So sánh trước/trong sự cố: RAG **0ms → 2500ms** (n=27 → n=5), LLM giữ nguyên 150ms.

- **Root cause:**
  Bước truy xuất tài liệu (RAG) bị chèn một độ trễ cố định 2.5s. Bằng chứng khẳng định đây là độ trễ nhân tạo chứ không phải nghẽn tài nguyên: 5 request cho ra 2500/2500/2500/2500/2501ms — độ lệch chỉ 0–1ms, một hệ thống nghẽn thật không bao giờ đều như vậy. Xác nhận tại source: `app/mock_rag.py` gọi `time.sleep(2.5)` khi `STATE["rag_slow"]` được bật.

- **Phát hiện thêm — sự cố bị khuếch đại 5 lần:**
  Client đo 13.3s/request nhưng server chỉ ghi 2.65s. Chênh lệch đúng bằng `concurrency=5`. Nguyên nhân: `/chat` khai báo `async def` nhưng `agent.run()` là hàm đồng bộ có `time.sleep()` — gọi `time.sleep()` trong coroutine sẽ **block event loop**, khiến 5 request đồng thời bị xếp hàng nối tiếp thay vì chạy song song (5 × 2.65s = 13.3s). Đây không phải nguyên nhân gốc nhưng là lỗi kiến trúc làm mọi sự cố RAG nghiêm trọng lên gấp `concurrency` lần.

- **Fix action:**
  1. Tắt sự cố: `python scripts/inject_incident.py --disable` → latency về **154ms** (từ 2655ms), xác nhận đúng nguyên nhân (request kiểm chứng `req-4ff8b73c`).
  2. Với hệ thống thật: đặt timeout cho lời gọi vector store và có đường lui (trả kết quả rỗng + hạ `quality_score`) thay vì để request treo theo RAG.
  3. Sửa lỗi khuếch đại: chuyển `agent.run()` sang chạy trong threadpool (`await run_in_threadpool(...)`) hoặc đổi `/chat` thành `def` thường để Starlette tự đẩy sang threadpool.

- **Preventive measure:**
  1. **Alert theo từng bước, không chỉ theo tổng latency.** Nhóm đã thêm log `rag_retrieved`/`llm_generated` kèm `latency_ms` riêng, nên có thể cảnh báo khi `rag_ms` vượt ngưỡng — phát hiện sớm hơn nhiều so với đợi tổng latency vượt SLO.
  2. **Ngưỡng alert chặt hơn SLO** (xem mục 5): sự cố này vượt 2000ms nhưng dưới SLO 3000ms.
  3. **Giữ span con cho mọi bước I/O.** Nếu trace chỉ có một span `run` thì việc khoanh vùng RAG vs LLM là bất khả thi.
  4. **Test tải với concurrency > 1 trong CI** để phát hiện sớm lỗi block event loop, vì với concurrency=1 lỗi này hoàn toàn vô hình.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Phạm Khánh Linh (E) | Setup + baseline CP0; tách span `rag-retrieve`/`llm-generate` và log latency theo bước; sửa lỗi mất trace do `LANGFUSE_TIMEOUT`; A/B prompt v1/v2; promote + rollback label `production`; chạy và điều tra challenge CP3; tổng hợp `REPORT.md` + evidence | | `tracing_enabled: true` chỉ nghĩa là có key, không đảm bảo trace đã lên được server — phải kiểm chứng bằng API. Một span duy nhất cho cả request là vô dụng khi debug. `time.sleep()` trong `async def` block cả event loop và khuếch đại sự cố theo số request đồng thời. |
| Lê Thị Yến Nhi (A) | | | |
| Nguyễn Văn Phong (B) | | | |
| Nguyễn Thanh Phúc (C) | | | |
| Vũ Huy Hoàng (D) | | | |
