# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Ngô Tuấn Tùng             |
| MSSV               | 2A202602826                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | IpadKids     |
| Vai trò chính    | Recovery & Phase 2                 |
| Repository         | https://github.com/tuantung26/K4-L3B-DAY10-IpadKids-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Xây dựng luồng Corruption & Repair | `src/pipelines/corruption_flow.py` (`run_corruption_flow_pipeline`) | `clean_csv`, `baseline_metrics` | `corrupted_clean_csv`, `corruption_report.md` | Hoàn thành |
| Hàm phục hồi dữ liệu gốc | `src/pipelines/corruption_flow.py` (`repair_from_raw_snapshot`) | `raw_records_json` | `repaired_clean_csv` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp luồng chạy chung | Cả nhóm / `script/run_corruption_flow.py` | Tạo điểm entrypoint để chạy kịch bản thử nghiệm |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Lắp ráp các bước pipeline | `src/pipelines/corruption_flow.py` | Pipeline code chuẩn template | Code review |
| Khôi phục snapshot | `repair_from_raw_snapshot` | Hàm đọc raw JSON và build dataframe mới | Code review |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Script tổng hợp gọi 8 bước kiểm thử (Corruption -> Evaluate -> Repair -> Evaluate -> Report) giúp nhóm xác minh sự khác biệt của metrics trước và sau khi dữ liệu bị hỏng.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Kiểm thử sức chịu đựng của hệ thống và quan sát hiện tượng "Silent Failure" (Hệ thống RAG vẫn chạy nhưng trả lời sai do dữ liệu nền bị hỏng), từ đó minh chứng sự cần thiết của Data Quality Gate và Freshness check. Đồng thời xây dựng cơ chế phục hồi tự động bằng cách tải lại snapshot gốc (raw data).

### Cách triển khai

Viết logic cho hàm `run_corruption_flow_pipeline` tuân thủ đúng 8 bước:
1. Load baseline metrics và clean data.
2. Gọi hàm corrupt làm hỏng dữ liệu.
3. Lưu lại bản corrupted.
4. Xây lại Vector Index (ChromaDB) và chạy tập test để đánh giá điểm.
5. Chạy Great Expectations (Quality checks) và Freshness report.
6. Kích hoạt `repair_from_raw_snapshot` để build lại clean data từ raw json.
7. Xây lại Index và đánh giá lại một lần nữa.
8. Gọi hàm tạo báo cáo so sánh 3 trạng thái.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings` object, `baseline_metrics`, `papers_clean.csv` |
| Output                         | Dữ liệu hỏng, dữ liệu sửa, Index tương ứng và `corruption_report.md` |
| Module phụ thuộc             | `ingestion.corruption`, `retrieval.index`, `observability.quality`, v.v. |
| Module sử dụng output        | Module báo cáo cuối cùng (`reporting.py`) |
| Điều kiện lỗi cần xử lý | Chưa có dữ liệu thật (thực hiện theo template logic) |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Mã chạy thành công 8 bước và sinh ra `data/reports/corruption_report.md`.
- **Kết quả thực tế:** Code đã sẵn sàng, chờ có dữ liệu để thực thi thực tế.
- **Artifact/log:** (Sẽ cập nhật sau khi chạy)

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần khôi phục dữ liệu đã bị hỏng trong pipeline.
- **Các phương án đã cân nhắc:** (1) Undo các thay đổi từ hàm corrupt. (2) Chạy lại toàn bộ ingestion từ đầu (gọi API). (3) Khôi phục bằng cách tải lại file raw_records_json (snapshot cục bộ).
- **Phương án đã chọn:** Phương án (3).
- **Lý do:** Trade-off tốt nhất. API có giới hạn rate-limit và có thể không ổn định, nên dùng snapshot lưu sẵn (raw json) giúp phục hồi nhanh, an toàn (reproducibility cao) mà không cần mạng.
- **Bằng chứng quyết định phù hợp:** Mã trong `repair_from_raw_snapshot` gọi thẳng `load_raw_records` thay vì `fetch_source_records`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Template có hàm `main()` nhưng không khớp với yêu cầu gọi `run_corruption_flow_pipeline`.
- **Lệnh hoặc bước tái hiện:** Kiểm tra template `src/pipelines/corruption_flow.py`.
- **Nguyên nhân gốc:** Template yêu cầu điền nhưng chưa thiết lập sẵn định dạng hàm `run_corruption_flow_pipeline` mong đợi.
- **Cách xử lý:** Xây dựng tường minh 2 hàm `repair_from_raw_snapshot(settings)` và `run_corruption_flow_pipeline(settings)` riêng biệt, sửa `main()` để gọi vào pipeline chính.
- **Cách xác minh sau khi sửa:** Check import và gọi hàm trong `script/run_corruption_flow.py`.
- **Điều học được:** Việc bám sát thiết kế và tái cấu trúc template theo hướng module hóa giúp pipeline dễ kiểm thử hơn.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
   Dữ liệu được tải qua API Crossref -> Lưu vào raw_records.json -> Làm sạch (loại bỏ bài thiếu abstract, nối tác giả) -> Lưu thành papers_clean.csv -> Embedding bằng MiniLM -> Lưu vector vào ChromaDB.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
   Hệ thống sẽ thử query từ Evaluation set, sau đó so sánh document ID truy xuất được với ground-truth để tính Hit Rate, và dùng prompt LLM/Ragas để chấm điểm câu trả lời (Answer Relevancy) so với ground-truth answer.
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
   Quality checks tập trung vào tính hợp lệ của schema (VD: text không rỗng, ID không null) thông qua Great Expectations. Freshness đánh giá xem dữ liệu có lỗi thời không (dựa trên age_days) đảm bảo hệ thống luôn phản hồi thông tin mới.
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
   Để có cơ sở so sánh công bằng (apple-to-apple) xem việc thay đổi chất lượng dữ liệu nền ảnh hưởng chính xác thế nào đến kết quả retrieval và sinh văn bản của LLM.
5. Repair được xem là thành công dựa trên artifact và metric nào?
   Khi metric (hit rate, token_f1, quality check) ở trạng thái Repaired khôi phục về xấp xỉ hoặc bằng với trạng thái Baseline.

## 8. Phân tích kết quả

### Metrics chính

*(Do hiện tại chưa có data để chạy, các kết quả bên dưới là giả định hoặc để trống)*

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      N/A |       N/A |      N/A | Dự kiến Corrupted sẽ giảm sâu |
| `mean_token_f1`      |      N/A |       N/A |      N/A | Dự kiến Corrupted sẽ giảm do sai nội dung |
| `judge_accuracy`     |      N/A |       N/A |      N/A | Tương tự token_f1 |
| `mean_judge_score`   |      N/A |       N/A |      N/A | Tương tự token_f1 |
| Quality checks         |     Pass |      Fail |     Pass | Corrupted sẽ fail các rule GE |
| Freshness status       |    Fresh |     Stale |    Fresh | Corrupted có thể mô phỏng dữ liệu cũ |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. Data corruption → Các cột quan trọng bị mất hoặc nhiễu (Quality fail) → Vector Index bị sai lệch khiến retrieval_hit_rate giảm mạnh → Answer sinh ra bị sai (Silent Failure).
2. Tải lại Raw Snapshot (Repair action) → Dữ liệu sạch được khôi phục, Quality/Freshness pass → Các agent metric phục hồi lại mức Baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Mất nội dung abstract (hoặc bị đổi thành rác) ảnh hưởng lớn nhất vì đây là vùng dữ liệu dùng để embedding. Khi bị hỏng, vector tạo ra không còn biểu diễn đúng ngữ nghĩa, khiến RAG truy xuất sai tài liệu.

Kết quả nào khác với kỳ vọng ban đầu?

Chưa có dữ liệu chạy thực tế.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Tầm quan trọng của việc sao lưu raw data để có phương án fallback an toàn và nhanh chóng.
2. Silent Failure cực kỳ nguy hiểm trong RAG vì LLM có thể vẫn trả lời tự tin nhưng dựa trên context sai; ta cần Data Observability để phát hiện kịp thời.
3. Việc kết hợp Great Expectations giúp định nghĩa rõ ràng hợp đồng dữ liệu (data contract), phát hiện hỏng hóc từ sớm trước khi nạp vào vector DB.

### Nếu có thêm thời gian

Tôi sẽ viết thêm unit test để tự động kiểm thử hàm `repair_from_raw_snapshot`, mock dữ liệu để đảm bảo luồng repair luôn đúng trong mọi hoàn cảnh.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Ngô Tuấn Tùng
**Ngày xác nhận:** 2026-09-26
