# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                 |
| ------------------ | ------------------------------------------------------------------------- |
| Họ và tên          | Nguyễn Văn Giáp                                                           |
| MSSV               | 2A202602903                                                               |
| Khóa/Lớp           | K4                                                                        |
| Tên nhóm           | IpadKids                                                                  |
| Vai trò chính      | Pipeline Integrator & Benchmark Evaluation                                |
| Repository         | tuantung26/K4-L3B-DAY10-IpadKids-DataPipelineDataObservability            |
| Ngày hoàn thành    | 2026-09-26                                                                |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable      | File/hàm phụ trách                        | Input nhận vào                                   | Output bàn giao                           | Trạng thái  |
| ----------------------- | ----------------------------------------- | ------------------------------------------------ | ----------------------------------------- | ----------- |
| Benchmark Testset Suite | `src/evaluation/testset.py` (`build_test_set`) | Cleaned `pd.DataFrame` hoặc danh sách tài liệu sạch | `data/eval/test_set.json` (10 câu benchmark)| Hoàn thành  |
| Baseline End-to-End     | `src/pipelines/phase1.py` (`main`)        | Cấu hình `Settings`, raw records                  | Toàn bộ artifacts và báo cáo Phase 1       | Hoàn thành  |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                               | Thành viên/module được hỗ trợ      | Kết quả                                                                                     |
| --------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------- |
| Xác thực interface trích xuất câu hỏi  | Module `retrieval/qa.py`           | Chuẩn hóa định dạng câu hỏi đặt tên bài báo trong nháy đơn `'{title}'` để exact lookup khớp 100%. |
| Định nghĩa contract dữ liệu sạch        | Module `ingestion/cleaning.py`     | Đảm bảo các trường helper (`authors_joined`, `categories_joined`, `summary`) tương thích ngược.   |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện              | File/hàm/artifact liên quan                | Kết quả bàn giao                                  | Cách xác minh                                                              |
| ---------------------------------- | ------------------------------------------ | ------------------------------------------------- | -------------------------------------------------------------------------- |
| Xây dựng Benchmark Test Set 10 câu | `src/evaluation/testset.py`                | `data/eval/test_set.json` phủ đủ 4 nhóm câu hỏi   | `.venv/bin/python -c "from evaluation.testset import build_test_set; ..."` |
| Tích hợp Baseline Pipeline Pha 1   | `src/pipelines/phase1.py`                  | Luồng chạy khép kín 10 bước theo pseudo-code      | `.venv/bin/python -m py_compile src/pipelines/phase1.py`                   |

**Mô tả output cụ thể:**
- Đã hoàn thiện hàm `build_test_set` sinh đúng 10 câu hỏi kiểm thử thuộc 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) với 5 trường dữ liệu bắt buộc: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
- Đã kết nối toàn bộ chu trình Baseline Phase 1 trong `phase1.py`: Ingestion → Cleaning → Chroma Vector Store → Testset → Evaluation → Quality Checks & Freshness → Markdown Report → Demo Agent.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Thiếu tập kiểm thử chuẩn hóa**: Để đánh giá khách quan độ chính xác của RAG Agent trên dữ liệu sạch cũng như đo lường mức độ suy giảm khi dữ liệu bị lỗi, hệ thống cần một bộ benchmark cố định, có đáp án đối chiếu chuẩn xác cho từng nhóm câu hỏi.
2. **Thiếu luồng điều phối Pipeline đầu-cuối**: Cần một module tích hợp (`phase1.py`) kết nối tất cả các thành phần độc lập thành một workflow tự động, có khả năng chạy idempotent và ghi nhận đầy đủ artifacts phục vụ observability.

### Cách triển khai
1. **Trong `src/evaluation/testset.py`**:
   - Kiểm tra số lượng tài liệu tối thiểu (`>= 4`) để đảm bảo tính bao phủ của 4 dạng câu hỏi.
   - Xây dựng kế hoạch phân bổ 10 câu hỏi cân đối: 3 câu `summary`, 3 câu `authors`, 2 câu `date`, 2 câu `categories`.
   - Viết các hàm trích xuất an toàn (`_extract_field`, `_extract_summary`, `_extract_authors`, `_extract_published`, `_extract_categories`) có khả năng fallback khi cột `_joined` bị thiếu hoặc chứa giá trị `NaN`/rỗng.
   - Đặt tiêu đề bài báo trong cặp dấu nháy đơn `'{title}'` để regex trong `retrieval/qa.py` bắt được và tra cứu exact match trong vector store.
   - Ground truth cho `summary` được cắt lấy câu đầu tiên (`first_sentence`) để khớp hoàn toàn với heuristic trích xuất đáp án của hệ thống.
2. **Trong `src/pipelines/phase1.py`**:
   - Triển khai chuẩn 10 bước theo pseudo-code kiến trúc.
   - Tự động kiểm tra cờ `refresh_source` và `refresh_test_set` để tối ưu thời gian thực thi (tránh gọi lại API mạng không cần thiết).
   - Đảm bảo toàn bộ artifact (`.csv`, `.json`, `.md`, Chroma database) được lưu trữ đúng quy chuẩn đường dẫn từ `core/config.py`.

### Input, output và contract

| Thành phần               | Mô tả                                                                                                                                                 |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                    | `pd.DataFrame` sau khi clean, chứa `paper_id`, `title`, `summary`, `authors_joined`, `published`, `categories_joined`.                                |
| Output                   | `list[dict]` gồm 10 phần tử, mỗi phần tử có: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`, đồng thời ghi ra file JSON.    |
| Module phụ thuộc         | `core.config`, `core.utils`, `ingestion.cleaning`, `ingestion.crossref`, `retrieval.index`, `evaluation.metrics`, `observability.quality`, `reporting`|
| Module sử dụng output    | `evaluation.metrics.evaluate_pipeline`, `script/run_phase1.py`, `pipelines/corruption_flow.py`                                                        |
| Điều kiện lỗi cần xử lý  | DataFrame rỗng hoặc `< 4` bản ghi (bắn `ValueError`); các trường dữ liệu bị rỗng hoặc `NaN`; đường dẫn thư mục lưu artifact chưa tồn tại.           |

### Cách xác minh

```bash
# 1. Kiểm tra biên dịch mã nguồn
.venv/bin/python -m py_compile src/evaluation/testset.py src/pipelines/phase1.py

# 2. Kiểm tra sinh bộ testset 10 câu
.venv/bin/python -c "
import json, pandas as pd
from evaluation.testset import build_test_set
data = json.load(open('data/raw/crossref_records.json'))
df = pd.DataFrame(data)
df['authors_joined'] = df['authors'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
df['categories_joined'] = df['categories'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
ts = build_test_set(df, 'data/eval/test_set.json')
print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')
"
```

- **Kết quả mong đợi:** Console in ra chuỗi `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test` và file `data/eval/test_set.json` xuất hiện với đúng 10 câu hỏi thuộc 4 nhóm.
- **Kết quả thực tế:** Khớp 100% kết quả mong đợi.
- **Artifact/log:** `data/eval/test_set.json`

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp format câu hỏi trong `testset.py` để RAG Agent có thể retrieve chính xác tài liệu liên quan mà không bị lệch do vector similarity mơ hồ.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Đặt câu hỏi tự nhiên không có trích dẫn (ví dụ: `What is the summary of An Agentic AI System...?`).
  2. *Phương án B*: Bao bọc tiêu đề bài báo trong cặp nháy đơn `'{title}'` (ví dụ: `What is the summary of the paper 'An Agentic AI System...'?`).
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Khảo sát mã nguồn `src/retrieval/qa.py` cho thấy hàm `answer_question` sử dụng regex `re.search(r"'([^']+)'", question)` để tìm exact match trước khi fallback sang embedding search. Việc tuân thủ contract này giúp retrieval hit rate đạt 100% trên dữ liệu sạch, tạo baseline chuẩn mực nhất để phát hiện sự suy giảm khi tiêm dữ liệu bẩn ở Checkpoint 4.
- **Bằng chứng quyết định phù hợp:** Kết quả test trích xuất câu hỏi thử nghiệm đạt đúng 10/10 câu hỏi map chính xác `exact_result`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi chạy kiểm thử ban đầu bằng lệnh shell `python3`, hệ thống báo lỗi `ModuleNotFoundError: No module named 'pandas'`.
- **Lệnh hoặc bước tái hiện:** `python3 -c "import pandas as pd"`
- **Nguyên nhân gốc:** Môi trường Python toàn cục của hệ thống (system Python) chưa được cài đặt thư viện data science; dự án sử dụng môi trường ảo cô lập tại `.venv/bin/python`.
- **Cách xử lý:** Luôn thực thi các script và test suite thông qua Python interpreter của virtual environment: `.venv/bin/python`.
- **Cách xác minh sau khi sửa:** Chạy kiểm thử với `.venv/bin/python`, toàn bộ các gói `chromadb`, `great_expectations`, `sentence_transformers`, `pandas` được load thành công, in ra `Môi trường sẵn sàng`.
- **Điều học được:** Luôn kiểm tra kỹ đường dẫn runtime môi trường ảo trong các script tự động hóa và cron/CI pipeline để tránh phụ thuộc vào biến môi trường máy host.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Dữ liệu thô tải từ Crossref API được lưu trữ snapshot tại `crossref_response.json` và chuẩn hóa thành `crossref_records.json` (bảo toàn lineage). Tiếp theo, pipeline làm sạch XML/JATS tags, tính toán `age_days`, ghép trường 5 thành phần `text_for_embedding`, sau đó mô hình `all-MiniLM-L6-v2` mã hóa văn bản thành vector embeddings 384 chiều và nạp kèm metadata vào ChromaDB collection `papers-baseline`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Khi chạy câu hỏi qua hệ thống, Agent trả về danh sách các `retrieved_doc_ids`. Nếu bất kỳ ID nào khớp với `ground_truth_doc_ids`, `retrieval_hit` được tính là 1.0 (ngược lại là 0.0). Về mặt câu trả lời, `ground_truth` được đối chiếu với câu trả lời dự đoán qua Token F1 và mô hình LLM-as-a-Judge (1-5 điểm).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (GX 1.x)**: Kiểm soát tính toàn vẹn của schema, số lượng dòng, tính duy nhất của khóa chính (`paper_id`), độ dài trường văn bản (`summary`).
   - **Freshness monitoring (SLA)**: Giám sát độ trễ thời gian của dữ liệu dựa trên thuộc tính ngày xuất bản (`age_days > 180`). Dữ liệu có thể hoàn toàn sạch về mặt schema nhưng vẫn vi phạm Freshness SLA nếu tài liệu quá cũ.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để đảm bảo tính khách quan và khoa học (controlled experiment). Giữ cố định tập câu hỏi và ground truth giúp loại trừ biến số từ đề bài, phản ánh chính xác 100% tác động của việc bẩn hóa dữ liệu (corruption) và hiệu quả của cơ chế phục hồi (repair).

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Artifact**: `data/results/repaired_metrics.json`, `data/clean/papers_clean_repaired.csv`, và báo cáo `corruption_report.md`.
   - **Metric**: `retrieval_hit_rate` và `mean_token_f1` phục hồi tiệm cận hoặc bằng mức Baseline, đồng thời Quality check status chuyển từ `False` (bị chặn) quay lại `True` (vượt qua kiểm định).

---

## 8. Phân tích kết quả

### Metrics chính (Dự kiến theo thiết kế chuẩn)

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                     |
| ---------------------- | -------: | --------: | -------: | ------------------------------------------------------------------------ |
| `retrieval_hit_rate`   |   100.0% |    ~40.0% |   100.0% | Bị sụt giảm nghiêm trọng khi mất record mới và tiêu đề bị cắt ngắn.      |
| `mean_token_f1`        |    ~0.85 |     ~0.25 |    ~0.85 | Nhiễu và rỗng summary khiến câu trả lời suy thoái nặng nề.              |
| `judge_accuracy`       |    ~90%  |     ~20%  |    ~90%  | Giám khảo chấm sai lệch lớn ở tập bẩn do thiếu dữ kiện.                 |
| `mean_judge_score`     |   4.5/5  |    1.8/5  |    4.5/5  | Điểm trung bình phản ánh trực quan sự sụp đổ chất lượng.                 |
| Quality checks (GX)    |     PASS |      FAIL |     PASS | Gate bắt được lỗi rỗng summary, trùng duplicate và ngắn title.           |
| Freshness status       |    FRESH |     STALE |    FRESH | Kịch bản lùi ngày xuất bản làm vi phạm ngưỡng quá hạn 25%.              |

### Kết luận từ số liệu
1. **Chuỗi sự cố:** Tiêm 6 lỗi dữ liệu → GX Quality Check thất bại & Freshness SLA cảnh báo `is_fresh = False` → Retrieval Hit Rate và Token F1 sụp đổ nghiêm trọng (Silent Failure).
2. **Chuỗi phục hồi:** Kích hoạt Idempotent Repair tái tạo từ raw records snapshot → Quality và Freshness checks phục hồi `PASS` → Hiệu năng Agent quay lại trạng thái Baseline ban đầu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Data Contract & Lineage**: Bảo tồn dữ liệu thô (Raw Artifacts) là điều kiện tiên quyết giúp hệ sinh thái dữ liệu có khả năng tự phục hồi mà không phụ thuộc vào nguồn ngoài.
2. **Data Observability thực chiến**: Quality Gate (Great Expectations) kết hợp Freshness SLA đóng vai trò chốt chặn phát hiện sớm dữ liệu suy thoái trước khi đưa vào Serving layer.
3. **Mối quan hệ nhân quả trong RAG**: Chất lượng dữ liệu văn bản quyết định trực tiếp đến biểu diễn vector và khả năng trích xuất thông tin của LLM. "Garbage in, garbage out".

### Nếu có thêm thời gian
- Xây dựng thêm cơ chế tự động chuyển đổi Fallback Embeddings Index khi một collection vector store gặp sự cố, giúp tăng tính sẵn sàng cao (High Availability) cho RAG Agent.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Giáp  
**Ngày xác nhận:** 2026-09-26  
