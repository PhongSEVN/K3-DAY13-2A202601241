# Alert và Runbook

Mỗi alert trong hệ thống được thiết kế theo hướng **symptom-based**, tức là dựa trên triệu chứng người dùng gặp phải hoặc dựa trên việc vi phạm SLO. Alert không phụ thuộc trực tiếp vào tên class, function hoặc module triển khai nội bộ.

## Alert 1

* **Tên:** High Latency P95
* **Severity:** warning
* **SLI/SLO liên quan:** `latency_p95_ms <= 3000 ms`
* **Điều kiện và thời gian duy trì:** Kích hoạt khi `latency_p95_ms > 3000` liên tục trong 5 phút.
* **Ảnh hưởng tới người dùng:** Người dùng phải chờ lâu hơn để nhận phản hồi. Nếu latency tiếp tục tăng, request có thể bị timeout hoặc trải nghiệm sử dụng bị giảm đáng kể.
* **Ba bước kiểm tra đầu tiên:**

  1. Kiểm tra dashboard để xác nhận P95 latency vượt ngưỡng 3000 ms và xác định khoảng thời gian xảy ra bất thường.
  2. Mở các trace có latency cao trong khoảng thời gian đó để xác định span nào chiếm nhiều thời gian xử lý nhất.
  3. Dùng trace ID hoặc correlation ID để tìm log tương ứng và kiểm tra timeout, lỗi hoặc bước xử lý bị chậm.
* **Mitigation tạm thời:** Giảm tải nếu hệ thống đang quá tải, giới hạn concurrency nếu cần, ưu tiên request quan trọng và chuyển sang model hoặc dịch vụ dự phòng có latency thấp hơn nếu hệ thống hỗ trợ.
* **Owner:** Vũ Huy Hoàng

## Alert 2

* **Tên:** High Error Rate
* **Severity:** critical
* **SLI/SLO liên quan:** `error_rate_pct <= 2%`
* **Điều kiện và thời gian duy trì:** Kích hoạt khi `error_rate_pct > 2` liên tục trong 5 phút.
* **Ảnh hưởng tới người dùng:** Một phần request không được xử lý thành công. Người dùng có thể không nhận được câu trả lời, nhận lỗi hoặc phải gửi lại request nhiều lần.
* **Ba bước kiểm tra đầu tiên:**

  1. Kiểm tra dashboard để xác nhận error rate vượt 2% và xem loại lỗi nào xuất hiện nhiều nhất.
  2. Mở các trace thất bại trong cùng khoảng thời gian để xác định span hoặc bước xử lý xảy ra lỗi.
  3. Dùng trace ID hoặc correlation ID để tìm log tương ứng và kiểm tra `error_type`, thông báo lỗi cùng các metadata liên quan.
* **Mitigation tạm thời:** Retry có kiểm soát đối với lỗi tạm thời, giảm tải nếu hệ thống quá tải, sử dụng fallback nếu có và rollback thay đổi gần nhất nếu có bằng chứng cho thấy thay đổi đó gây ra lỗi.
* **Owner:** Vũ Huy Hoàng

## Alert 3

* **Tên:** Cost or Quality SLO Breach
* **Severity:** warning
* **SLI/SLO liên quan:** `daily_cost_usd <= 2.5` và `quality_score_avg >= 0.75`
* **Điều kiện và thời gian duy trì:** Kích hoạt khi `daily_cost_usd > 2.5` hoặc `quality_score_avg < 0.75`.
* **Ảnh hưởng tới người dùng:** Nếu quality giảm, người dùng có thể nhận được câu trả lời kém chính xác hoặc ít hữu ích hơn. Nếu cost tăng cao, hệ thống có nguy cơ vượt ngân sách vận hành.
* **Ba bước kiểm tra đầu tiên:**

  1. Kiểm tra dashboard để xác định vi phạm đến từ cost, quality hoặc cả hai.
  2. Nếu cost tăng, kiểm tra traffic, số token input/output và các trace có chi phí cao bất thường. Nếu quality giảm, kiểm tra các trace có `quality_score` thấp.
  3. Dùng trace ID hoặc correlation ID để tìm log tương ứng và kiểm tra model, token usage, feature, latency và các metadata liên quan.
* **Mitigation tạm thời:** Nếu cost cao, giảm token không cần thiết, giới hạn output hoặc chuyển sang model có chi phí thấp hơn nếu phù hợp. Nếu quality thấp, rollback prompt về phiên bản ổn định trước đó hoặc chuyển sang cấu hình/model đã được xác nhận có chất lượng tốt hơn.
* **Owner:** Vũ Huy Hoàng
