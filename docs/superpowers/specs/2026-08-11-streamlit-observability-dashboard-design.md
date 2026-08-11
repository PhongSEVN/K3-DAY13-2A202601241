# Thiết kế Streamlit Observability Dashboard

## Mục tiêu

Xây dựng dashboard runtime bằng Streamlit, đọc nguồn chuẩn `data/logs.jsonl` và hiển thị đúng sáu nhóm thông tin trong `config/dashboard.yaml`. Dashboard ưu tiên đáp ứng rubric, dễ chụp evidence và hỗ trợ bước đầu của luồng điều tra Metrics → Traces → Logs.

## Phạm vi

Dashboard bao gồm:

- Sáu panel bắt buộc trong bố cục lưới 3 × 2.
- Cửa sổ thời gian mặc định 60 phút.
- Tự làm mới mỗi 30 giây.
- Đơn vị, threshold và trạng thái đạt/vi phạm rõ ràng.
- Một bảng request bất thường ở cuối trang để hỗ trợ điều tra. Bảng này không được tính là panel thứ bảy.

Dashboard không bao gồm xác thực người dùng, lưu trữ dữ liệu riêng, chỉnh sửa dashboard bằng UI hoặc tích hợp trực tiếp với Langfuse.

## Công nghệ

- Streamlit: giao diện, layout, trạng thái và refresh.
- Pandas: đọc, chuẩn hóa, lọc và tổng hợp dữ liệu JSONL.
- Altair: biểu đồ và đường threshold.

Các dependency được khai báo rõ trong `requirements.txt`. Dashboard chạy bằng:

```bash
uv run streamlit run dashboard/app.py
```

## Kiến trúc

Dashboard được chia thành hai module có ranh giới rõ ràng:

- `dashboard/data.py`: đọc JSONL, chuẩn hóa timestamp, lọc cửa sổ thời gian và tính metric. Module không phụ thuộc Streamlit để có thể unit test độc lập.
- `dashboard/app.py`: cấu hình trang, refresh, bố cục lưới và render dữ liệu bằng Streamlit/Altair.

Luồng dữ liệu:

```text
data/logs.jsonl
    → đọc và kiểm tra từng dòng
    → DataFrame chuẩn hóa
    → lọc 60 phút gần nhất theo thời gian hiện tại
    → phân loại event và tính sáu nhóm metric
    → render lưới Streamlit 3 × 2
```

`dashboard/data.py` trả về dữ liệu và kết quả tổng hợp qua các hàm có đầu vào/đầu ra rõ ràng. `dashboard/app.py` không tự tính lại metric nghiệp vụ.

## Bố cục giao diện

Đầu trang hiển thị tiêu đề, cửa sổ “Last 60 minutes”, thời điểm cập nhật cuối và trạng thái refresh 30 giây.

Sáu panel được xếp theo thứ tự:

```text
Latency        | Traffic        | Errors
Cost           | Tokens         | Quality
```

Mỗi panel gồm tên, metric chính, đơn vị, threshold, trạng thái đạt/vi phạm và biểu đồ phù hợp. Bảng “Recent anomalous requests” nằm dưới lưới, chứa tối đa các request chậm hoặc lỗi gần nhất với các cột có sẵn: timestamp, correlation ID, feature, latency và error type.

## Định nghĩa panel

### 1. Latency percentiles

- Nguồn: event `response_sent`.
- Field: `latency_ms`.
- Metric: P50, P95 và P99 trong cửa sổ.
- Biểu đồ: latency theo thời gian.
- Đơn vị: `ms`.
- Đạt khi P95 không vượt quá `3000 ms`.

### 2. Request traffic

- Nguồn: event `request_received`.
- Metric: tổng request trong cửa sổ và số request theo từng phút.
- Biểu đồ: request count theo phút.
- Đơn vị: `requests_per_minute`.
- Đường tham chiếu: `1 request/phút` theo contract.

Các phút không có event được hiển thị là 0 khi nằm giữa phút đầu và phút cuối có dữ liệu. Khi toàn cửa sổ không có request, panel hiển thị `N/A` thay vì báo vi phạm giả.

### 3. Error rate and breakdown

- Tử số: số event `request_failed`.
- Mẫu số: số event `request_received`.
- Công thức: `request_failed / request_received × 100`.
- Breakdown: số lỗi theo `error_type`; giá trị thiếu được gắn nhãn `unknown`.
- Đơn vị: `%`.
- Đạt khi error rate không vượt quá `2%`.
- Nếu không có request nhận vào, error rate là `N/A`.

### 4. Cost over time

- Nguồn: event `response_sent`.
- Field: `cost_usd`.
- Metric: tổng theo phút và tổng toàn cửa sổ.
- Đơn vị: `USD`.
- Đạt khi tổng toàn cửa sổ không vượt quá `$2.50`.

### 5. Input and output tokens

- Nguồn: event `response_sent`.
- Fields: `tokens_in`, `tokens_out`.
- Metric: tổng riêng từng field.
- Biểu đồ: so sánh input/output token.
- Đơn vị: `tokens`.
- Threshold `50000` được đánh giá riêng cho tổng input và tổng output, đúng aggregation `sum_by_field`. Panel đạt khi cả hai tổng không vượt threshold.

### 6. Quality proxy

- Nguồn: event `response_sent`.
- Field: `quality_score`.
- Metric: trung bình trong cửa sổ.
- Biểu đồ: quality theo thời gian.
- Đơn vị: `score_0_to_1`.
- Đạt khi trung bình không thấp hơn `0.75`.

## Cửa sổ thời gian và refresh

Dashboard dùng thời gian hiện tại làm điểm cuối và lọc record có timestamp trong 60 phút gần nhất. Timestamp được chuẩn hóa thành UTC trước khi so sánh. Giao diện tự làm mới mỗi 30 giây và đọc lại file, không giữ bản sao dữ liệu lâu dài.

## Xử lý lỗi

- Nếu `data/logs.jsonl` không tồn tại, dashboard hiển thị hướng dẫn chạy API và load test.
- File rỗng hoặc không có record hợp lệ tạo trạng thái empty, không gây crash.
- Dòng JSON hỏng hoặc timestamp không hợp lệ bị bỏ qua; giao diện hiển thị số record đã bỏ qua.
- Record thiếu field không được đưa vào phép tính cần field đó. Dashboard không tự điền số 0 cho metric bị thiếu.
- Panel không có dữ liệu trong cửa sổ hiển thị `N/A` và thông báo “No data in selected window”.
- Phép chia error rate có mẫu số bằng 0 trả về `N/A`.
- Lỗi đọc file do file đang được ghi được hiển thị thành cảnh báo; lần refresh tiếp theo sẽ thử lại.

## Kiểm thử và xác minh

Unit test cho `dashboard/data.py` bao phủ:

- Đọc JSONL hợp lệ và bỏ qua dòng hỏng.
- Chuẩn hóa timestamp và lọc đúng 60 phút.
- Tính P50/P95/P99.
- Tính traffic theo phút.
- Tính error rate và xử lý mẫu số 0.
- Tính cost, tổng token theo từng field và quality trung bình.
- Xử lý file rỗng, file thiếu và record thiếu field.

Xác minh hoàn tất gồm:

```bash
uv run python -m pytest -q
uv run python scripts/validate_dashboard.py
uv run streamlit run dashboard/app.py
```

Validator phải báo `HỢP LỆ: 6/6 panel`. Evidence runtime phải nhìn thấy tên sáu panel, cửa sổ 60 phút, đơn vị và threshold. Sau baseline, chạy practice `rag_slow` với cùng concurrency và chứng minh P95 tăng trước khi tắt incident.

## Tiêu chí hoàn thành

- Dashboard chạy từ repo bằng một lệnh đã nêu.
- Đúng nguồn `data/logs.jsonl` và đúng sáu panel contract.
- Tất cả metric dùng đúng event, field, aggregation và threshold.
- Empty/error state không làm ứng dụng crash hoặc hiển thị số liệu giả.
- Public tests và test dashboard đều đạt.
- Validator đạt 6/6 và có ảnh baseline cùng ảnh incident phù hợp để nộp.
