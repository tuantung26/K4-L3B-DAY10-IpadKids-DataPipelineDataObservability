# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4              |
| Tên nhóm         | IpadKids     |
| Repository         | https://github.com/tuantung26/K4-L3B-DAY10-IpadKids-DataPipelineDataObservability |
| Ngày hoàn thành | 26/09/2026               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Ngô Tuấn Tùng | 2A202602826 | Recovery & Phase 2 | `data/reports/corruption_report.md`, `script/run_corruption_flow.py` |
| 2 | Nguyễn Văn Giáp | 2A202602903 | Evaluation & Phase 1 | `data/eval/test_set.json`, `data/reports/phase1_report.md`, `script/run_phase1.py` |
| 3 | Cao Đức Hiệp | 2A202602550 | Data Cleaning & Quality | `src/ingestion/cleaning.py`, `src/observability/quality.py` |
| 4 | Phùng Đình Triển | 2A202602837 | Data Ingestion | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/results/corruption_log.json` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**
Nhóm IpadKids đã hoàn thiện toàn bộ end-to-end Data Pipeline bao gồm cả 2 giai đoạn: Phase 1 (Baseline Pipeline) và Phase 2 (Corruption & Recovery Flow). Ở Baseline pipeline, nhóm đã thu thập thành công 24 bản ghi thô từ Crossref API, tiến hành làm sạch, lập chỉ mục (index) lên ChromaDB, và xây dựng hệ thống Quality Gate thông qua Great Expectations (GX 1.x) để đảm bảo dữ liệu luôn đạt chất lượng. Baseline pipeline đã tạo ra các artifact cốt lõi như `papers_clean.csv`, `baseline_metrics.json`, và `phase1_report.md`. 
Trong Phase 2, nhóm đã kích hoạt các kịch bản corruption, trong đó việc làm rỗng summary và cắt xén title có tác động rõ rệt nhất đến hiệu năng của agent (gây hiện tượng Silent Failure với Hit Rate giảm từ 100% xuống 60%, Token F1 giảm một nửa). Cuối cùng, thông qua kịch bản Idempotent Repair (tái phục hồi từ raw snapshot), nhóm đã tái thiết lập thành công trạng thái sạch, khôi phục toàn bộ các chỉ số về mức chuẩn ban đầu. Vấn đề lớn nhất là việc giả lập Silent failure yêu cầu tuỳ chỉnh lại cơ chế query metadata để bỏ qua KeyError khi thiếu cột.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API | Fetch JSON, lưu raw records | `data/raw/crossref_records.json` | Phùng Đình Triển |
| Cleaning          | Raw records | Chuẩn hoá date, ghép chuỗi text | `data/clean/papers_clean.csv` | Cao Đức Hiệp |
| Embedding/index   | Cleaned CSV | Chunking, tạo Embeddings | `data/embeddings/embeddings.json` | Ngô Tuấn Tùng |
| Evaluation        | ChromaDB Index | Tạo testset, QA RAG, chấm F1 | `data/results/baseline_metrics.json` | Nguyễn Văn Giáp |
| Observability     | Cleaned CSV | Rule-based checking với GX | `data/reports/phase1_report.md` | Cao Đức Hiệp |
| Corruption/repair | Cleaned CSV | Inject noise, Duplicate, Repair | `data/reports/corruption_report.md` | Ngô Tuấn Tùng |
| Orchestration     | Toàn bộ Pipeline | Trigger chạy tuần tự các bước | Terminal Console | Ngô Tuấn Tùng |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | Gemini         |
| `LLM_MODEL`                | gemini-2.5-flash         |
| Embedding model              | all-MiniLM-L6-v2         |
| Số lượng Crossref records | 24         |
| Retrieval`top_k`           | 3         |
| Freshness threshold          | 180         |
| Random seed, nếu có        | 42         |

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 26/09/2026 12:29                  | Log Terminal + `phase1_report.md` |
| Corruption flow   | Thành công | 26/09/2026 12:35                  | Log Terminal + `corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref Works API |
| Query/filter                | "RAG", "LLM", "Data Pipeline"                  |
| Thời điểm lấy dữ liệu | 26/09/2026                           |
| Số record nhận được    | 24                         |
| Cơ chế retry/backoff      | Exponential backoff sử dụng thư viện tenacity                       |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | Chuỗi | Có | ID duy nhất bài báo | Báo lỗi hoặc drop dòng |
| `title` | Chuỗi | Có | Tựa bài báo | Báo lỗi nếu thiếu |
| `summary` | Chuỗi | Không | Abstract/Tóm tắt | Gán chuỗi rỗng |
| `published` | Ngày tháng | Không | Ngày xuất bản ISO | Gán None hoặc loại bỏ |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record không có title | Completeness  |              0 | Log Ingestion |
| Normalize ngày tháng về định dạng chuẩn | Validity                  |              24 | Test Quality Data |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:
- `text_for_embedding`: Ghép chuỗi Title, Authors, Categories, Published và Summary lại với nhau thành một string duy nhất có cấu trúc giúp VectorDB dễ dàng ánh xạ từ vựng.
- `document ID`: Ghép `paper_id` gốc với chỉ số index (VD: `10.xxxx::0`) đảm bảo tính unique.
- `age_days`: Tính hiệu số ngày giữa ngày hiện tại (`run_date`) và ngày `published`.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10                 |
| Các`question_type`                    | single_document, multi_document                  |
| Ground-truth document ID                 | Sinh tự động qua LLM từ corpus     |
| Embedding model                          | all-MiniLM-L6-v2                  |
| Vector store/collection                  | ChromaDB (`papers-baseline`)                 |
| Retrieval`top_k`                       | 3                   |
| LLM provider/model                       | Gemini (gemini-2.5-flash)                   |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:
Để tạo cơ sở đối chiếu tương đương (apple-to-apple). Nếu tập testset bị thay đổi, ta sẽ không thể đánh giá chính xác mức độ suy giảm do chất lượng tài liệu hay do câu hỏi thay đổi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | Đầy đủ dữ liệu thô |
| Cleaned dataset          | `data/clean/`                        | Có | |
| Embedding manifest/index | `data/embeddings/`                   | Có | |
| Evaluation set           | `data/eval/`                         | Có | 10 câu hỏi testset |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | |
| Quality/freshness        | `data/quality/`                      | Có | |
| Baseline report          | `data/reports/phase1_report.md`      | Có | |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     100.00% | Tỷ lệ ground truth document nằm trong top_k tìm kiếm |
| `mean_token_f1`      |     0.8000 | Điểm F1 trung bình trên tập token của câu trả lời                          |
| `judge_accuracy`     |     80.00% | Tỷ lệ LLM xác nhận câu trả lời khớp với thông tin thực tế                         |
| `mean_judge_score`   |     4.20 | Điểm số chất lượng câu trả lời trên thang 5                           |
| Ragas, nếu có        | N/A | Bỏ qua để tiết kiệm tài nguyên hệ thống |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `expect_table_row_count_to_be_between` | Completeness | >= 1 | PASS | Báo cáo GX |
| `expect_column_values_to_not_be_null` | Completeness | > 0 | PASS | Báo cáo GX |
| `expect_column_values_to_be_unique` | Uniqueness | True | PASS | Báo cáo GX |
| `expect_column_value_lengths_to_be_between` | Validity | > 30 | PASS | Báo cáo GX |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Tập dữ liệu DataFrame gốc            |
| Timestamp mới nhất       | 2026-09-04                         |
| Ngưỡng freshness         | 180 ngày                         |
| Trạng thái baseline      | FRESH               |
| Lý do                     | Tỷ lệ stale (chưa bị đổi) là 0% nằm dưới ngưỡng 25% |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Blank Summary | Điền chuỗi rỗng | 3 | Vi phạm Length/Null | Fail Expectation | Nạp lại từ Raw |
| Inject Noise | Chèn chuỗi rác `###@@@GARBAGE` | 3 | Có thể không phát hiện | Làm giảm F1 Score RAG | Nạp lại từ Raw |
| Stale Date | Trừ 365 ngày | 3 | Báo động Freshness SLA | Tỷ lệ stale tăng | Nạp lại từ Raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi nhận đầy đủ 6 thao tác corrupt và mảng ID các bài viết bị tác động.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:
Idempotent Repair được xây dựng bằng cách tải lại trực tiếp `raw_records.json` - bản snapshot nguyên thuỷ chưa qua chỉnh sửa lúc Fetch API. Từ bản snapshot này, chạy lại luồng clean, index và build lại collection ChromaDB. Nhờ vậy, trạng thái phục hồi được đảm bảo sạch 100% thay vì "sửa thủ công" từng dòng lỗi.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      100.00% |       60.00% |      100.00% |                      -40.00% |             +40.00% | Bị hỏng vector nghiêm trọng |
| `mean_token_f1`        |      0.8000 |       0.4000 |      0.8000 |                      -0.4000 |             +0.4000 | Trả lời chệch hướng |
| `judge_accuracy`       |      80.00% |       40.00% |      80.00% |                      -40.00% |             +40.00% | Chất lượng AI suy thoái |
| `mean_judge_score`     |      4.20 |       2.60 |      4.20 |                      -1.60 |             +1.60 | Thang điểm giảm |
| Quality checks pass/fail |      PASS |       FAIL |      PASS |                      FAIL |             PASS | Quality Gate chốt chặn thành công |
| Freshness status         |      FRESH |       FRESH |      FRESH |                      0 |             0 | Tỷ lệ stale lên 13.64% nhưng chưa quá ngưỡng 25% |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:
1. Việc chèn chuỗi nhiễu và làm rỗng dữ liệu Summary (Data corruption) → Vector Embeddings bị mất đi ý nghĩa hoặc thay đổi ngữ nghĩa trầm trọng → Retrieval Hit Rate giảm mạnh và kết quả trả về kém chất lượng.
2. Load lại Snapshot gốc và rebuild Index (Repair action) → Dữ liệu lấy lại định dạng gốc không bị thiếu (Quality signal phục hồi về PASS) → Hit Rate của Agent hồi lại mức tuyệt đối 100%.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** Khi chạy evaluation trên tập dữ liệu bị làm hỏng, hệ thống bị văng lỗi `KeyError: 'categories_joined'`.
- **Nguyên nhân:** Do dữ liệu bị làm hỏng (blank fields), quá trình đưa vào vector DB bị drop đi key metadata, dẫn tới hàm truy xuất QA extract answer bị lỗi KeyError do không tìm thấy giá trị.
- **Cách xử lý:** Thay đổi cách get dictionary trong `src/retrieval/qa.py` từ truy xuất cứng (`metadata['categories_joined']`) sang phương thức get có mặc định an toàn (`metadata.get('categories_joined', '')`).
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py` không còn văng lỗi và quan sát đúng hiện tượng Silent Failure.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Số lượng records khá nhỏ (24 rows) | Tính ngẫu nhiên cao, Hit Rate dễ đạt tuyệt đối | Tăng giới hạn lấy lên > 100 rows qua API Crossref |
| Cấu hình prompt RAG đang đơn giản | Câu trả lời đôi khi bị cụt | Nâng cấp Prompt Template cung cấp nhiều bối cảnh hơn |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
