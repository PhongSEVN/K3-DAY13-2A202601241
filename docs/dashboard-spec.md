# Yêu cầu dashboard

Contract có thể kiểm tra bằng máy nằm tại `config/dashboard.yaml`. Hướng dẫn dựng và kiểm tra runtime nằm tại [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md).

Dashboard chính cần đủ 6 nhóm thông tin:

1. Latency P50/P95/P99.
2. Traffic: request count hoặc QPS.
3. Error rate và breakdown theo loại lỗi.
4. Cost theo thời gian.
5. Tổng token input/output.
6. Quality proxy.

## Mapping panel → dữ liệu / SLO

| Panel ID | Event / field | Aggregation | Unit | Threshold (SLO line) |
|---|---|---|---|---|
| `latency` | `response_sent.latency_ms` | p50, p95, p99 | ms | p95 ≤ 3000 (`latency_p95_ms`) |
| `traffic` | `request_received` | count, rate_per_minute | requests_per_minute | rate ≥ 1 |
| `errors` | `request_received`, `request_failed`, `error_type` | error_rate_pct, count_by_value | percent | error_rate_pct ≤ 2 |
| `cost` | `response_sent.cost_usd` | sum_by_minute, total | usd | total ≤ 2.5 (`daily_cost_usd`) |
| `tokens` | `response_sent.tokens_in`, `tokens_out` | sum_by_field | tokens | sum ≤ 50000 |
| `quality` | `response_sent.quality_score` | mean | score_0_to_1 | mean ≥ 0.75 (`quality_score_avg`) |

Runtime tham chiếu: `streamlit run scripts/dashboard_app.py` (nguồn `data/logs.jsonl`).

Tiêu chuẩn trình bày:

- Khoảng thời gian mặc định: 1 giờ.
- Tự refresh mỗi 15–30 giây nếu công cụ hỗ trợ.
- Có threshold hoặc SLO line.
- Ghi rõ đơn vị.
- Chỉ giữ 6–8 panel quan trọng ở lớp chính.
- Screenshot phải nhìn được tên panel và khoảng thời gian.

Kiểm tra contract trước khi chụp evidence:

```bash
python scripts/validate_dashboard.py
```
