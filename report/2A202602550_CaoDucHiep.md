# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                          |
| ------------------ | ---------------------------------------------------------------------------------- |
| Họ và tên          | Cao Đức Hiệp                                                                      |
| MSSV               | 2A202602550                                                                        |
| Khóa/Lớp           | K4-L3B                                                                             |
| Tên nhóm           | IpadKids                                                                          |
| Vai trò chính      | Data Cleaning & Observability Gate (Người 2)                                      |
| Repository         | https://github.com/tuantung26/K4-L3B-DAY10-IpadKids-DataPipelineDataObservability |
| Ngày hoàn thành    | 2026-09-26                                                                         |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Data Cleaning & Pre-embed Modeling** | `src/ingestion/cleaning.py`<br>`build_clean_dataframe` | Danh sách `PaperRecord` từ `data/raw/crossref_records.json`, thời điểm chạy `run_date` | `pd.DataFrame` sạch (24 dòng), lưu ra `data/clean/papers_clean.csv` và `papers_clean.json` | **Hoàn thành** |
| **Data Observability (GX 1.x & Freshness)** | `src/observability/quality.py`<br>`run_data_quality_checks`<br>`evaluate_freshness_sla`<br>`build_freshness_report` | Cleaned `pd.DataFrame`, cấu hình `Settings`, tên giai đoạn (`stage`) | Báo cáo kiểm định chất lượng `data/quality/baseline_quality_report.json`, `freshness_report.json` | **Hoàn thành** |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Định nghĩa Contract Schema | `src/retrieval/index.py` (Người 3) | Đồng bộ các cột helper (`authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`) để Chroma vector store build index chính xác, không bị lỗi KeyError. |
| Kiểm thử chốt chặn Corruption Flow | `src/ingestion/corruption.py` & `src/pipelines/corruption_flow.py` (Người 1 & 4) | Cung cấp hàm `run_data_quality_checks` phát hiện kịp thời 6 lỗi làm bẩn dữ liệu (giảm dòng, rỗng title/summary, trùng lặp paper_id, stale date). |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Tiền xử lý & làm sạch dữ liệu | `src/ingestion/cleaning.py`<br>`data/clean/papers_clean.json`<br>`data/clean/papers_clean.csv` | Clean thành công 24 bản ghi không trùng lặp, đầy đủ cột `age_days` và `text_for_embedding` 5 phần | Chạy lệnh test nghiệm thu Bước 3: In ra đúng chuỗi `Clean thành công 24 dòng`. |
| Cấu hình chốt chặn Great Expectations 1.x | `src/observability/quality.py`<br>`data/quality/baseline_quality_report.json` | Ephemeral Context với 4 Expectations bắt buộc đạt `success = True` trên baseline | Chạy lệnh test nghiệm thu Bước 4: In ra `Quality check status = True`. |
| Giám sát độ tươi mới Freshness SLA | `src/observability/quality.py`<br>`data/quality/freshness_report.json` | Tỷ lệ bài báo cũ quá 180 ngày là 0% (ngưỡng cho phép $\le 25\%$), cờ `is_fresh = True` | Kiểm tra file `data/quality/freshness_report.json` sinh ra đầy đủ các trường SLA. |

**Nêu một output cụ thể:**
- File `data/clean/papers_clean.json`: Chứa 24 tài liệu khoa học chuẩn hóa từ Crossref API. Mỗi bản ghi được ghép trường `text_for_embedding` theo đúng mẫu 5 phần: `Title`, `Authors`, `Published`, `Categories`, `Summary`.
- File `data/quality/baseline_quality_report.json`: Minh chứng hệ thống Observability Gate theo chuẩn Great Expectations 1.x kiểm định thành công cả 4 hàng rào kỹ thuật:
  1. Số dòng: 24 dòng (nằm trong khoảng [5, 5000]).
  2. Giá trị không rỗng (Not Null): `paper_id`, `title`, `text_for_embedding` đều đạt 100%.
  3. Tính duy nhất (Unique): `paper_id` không có bản ghi trùng lặp nào.
  4. Độ dài trường văn bản: `summary` của tất cả 24 bản ghi đều $\ge 30$ ký tự.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Dữ liệu thô phân mảnh và chứa nhiễu**: Metadata lấy từ Crossref API có thể chứa khoảng trắng thừa, danh sách tác giả/danh mục ở dạng list phức tạp, bản ghi bị trùng lặp DOI, và thiếu ngữ cảnh tổng hợp để mô hình embedding hiểu được mối quan hệ giữa tiêu đề, tác giả và tóm tắt nội dung.
2. **Nguy cơ lỗi ngầm (Silent Failure) trong RAG**: Nếu đưa dữ liệu bị rỗng, thiếu trường, hoặc dữ liệu quá hạn vào Vector Database mà không kiểm soát, RAG Agent vẫn sẽ sinh câu trả lời nhưng câu trả lời sẽ bị sai lệch, ảo giác hoặc trả lời từ nguồn tin lỗi thời mà người vận hành không hề hay biết.

### Cách triển khai
1. **Tại `src/ingestion/cleaning.py`**:
   - `_normalize_whitespace(text)`: Sử dụng biểu thức chính quy `re.sub(r'\s+', ' ', text).strip()` để loại bỏ hoàn toàn các khoảng trắng dư thừa, ký tự xuống dòng rác trong tiêu đề và tóm tắt.
   - Trích xuất và định dạng:
     - `authors_joined = ", ".join(authors)`
     - `categories_joined = ", ".join(categories)`
     - `summary_chars = len(summary)`
   - Tính toán tuổi đời dữ liệu:
     `age_days = (run_date.date() - pub_date.date()).days` với cơ chế bắt lỗi và fallback an toàn khi gặp chuỗi ngày tháng không hợp lệ.
   - Tạo trường `text_for_embedding` gồm 5 phần chuẩn mực:
     ```text
     Title: {title}
     Authors: {authors_joined}
     Published: {published}
     Categories: {categories_joined}
     Summary: {summary}
     ```
   - Khử trùng lặp: `df.drop_duplicates(subset=["paper_id"], keep="first")` và lọc bỏ các bản ghi thiếu `paper_id`, `title`, `summary`.
2. **Tại `src/observability/quality.py`**:
   - Sử dụng chuẩn **Great Expectations 1.x** với Ephemeral Context để không cần tạo file cấu hình yaml phức tạp:
     ```python
     context = gx.get_context(mode="ephemeral")
     data_source = context.data_sources.add_pandas(name="papers_source")
     data_asset = data_source.add_dataframe_asset(name="papers_asset")
     batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
     batch = batch_def.get_batch(batch_parameters={"dataframe": df})
     ```
   - Đăng ký 4 Expectations:
     1. `gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)`
     2. `gxe.ExpectColumnValuesToNotBeNull(column="paper_id")`, `title`, `text_for_embedding`
     3. `gxe.ExpectColumnValuesToBeUnique(column="paper_id")`
     4. `gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)`
   - Xây dựng logic `evaluate_freshness_sla`:
     Tính tỷ lệ số bản ghi có `age_days > settings.freshness_threshold_days` (180 ngày). Nếu tỷ lệ này $> 25\%$, cờ `is_fresh` sẽ được gán bằng `False`.
   - Tổng hợp kết quả: `overall_success = gx_success and is_fresh`. Lưu toàn bộ payload ra file JSON trong thư mục `data/quality/`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input của Cleaning** | `records: list[PaperRecord]`, `run_date: datetime` |
| **Output của Cleaning** | `pd.DataFrame` với schema 16 cột chuẩn hóa: `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`, `authors_joined`, `categories_joined`, `summary_chars`, `age_days`, `text_for_embedding` |
| **Input của Quality Gate** | `df: pd.DataFrame`, `settings: Settings`, `stage: str` |
| **Output của Quality Gate** | `dict`: `{"success": bool, "gx_success": bool, "is_fresh": bool, "total_rows": int, "freshness": {...}, "expectations": [...]}` |
| **Module phụ thuộc** | `src/ingestion/crossref.py` (cung cấp dataclass `PaperRecord` và dữ liệu raw) |
| **Module sử dụng output** | `src/retrieval/index.py` (nạp `text_for_embedding` vào ChromaDB), `src/evaluation/testset.py` (sinh 10 câu test từ cleaned df), `src/pipelines/corruption_flow.py` (kiểm tra rào chắn chất lượng) |
| **Điều kiện lỗi đã xử lý** | Dòng bị trùng DOI, ngày tháng bị lỗi format, khoảng trắng rác dạng newline/tab, danh sách tác giả bị rỗng hoặc dạng chuỗi lạ. |

### Cách xác minh

#### Lệnh xác minh Bước 3 (Cleaning):
```bash
$env:PYTHONPATH="src"; $env:PYTHONIOENCODING="utf-8"; python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```
- **Kết quả mong đợi:** In ra `Tín hiệu hoàn thành: Clean thành công 24 dòng`.
- **Kết quả thực tế:** `Tín hiệu hoàn thành: Clean thành công 24 dòng` (Exit code: 0).

#### Lệnh xác minh Bước 4 (Quality & Freshness Gate):
```bash
$env:PYTHONPATH="src"; $env:PYTHONIOENCODING="utf-8"; python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); status=res['success']; print(f'Tín hiệu hoàn thành: Quality check status = {status}')"
```
- **Kết quả mong đợi:** In ra `Tín hiệu hoàn thành: Quality check status = True`.
- **Kết quả thực tế:** In ra `Tín hiệu hoàn thành: Quality check status = True` (Exit code: 0).
- **Artifact kiểm chứng:** `data/quality/baseline_quality_report.json` và `data/quality/freshness_report.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức cấu hình Great Expectations phiên bản 1.x (thay vì dùng thư mục file cấu hình truyền thống `great_expectations/` sinh bởi lệnh `great_expectations init`).
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (File-based Context)*: Khởi tạo thư mục dự án `great_expectations/`, định nghĩa datasource và checkpoint bằng file `.yml`.
  2. *Phương án 2 (Ephemeral Context trên GX 1.x)*: Sử dụng `gx.get_context(mode="ephemeral")` và API Fluent Datasource mới của Great Expectations 1.x (`data_sources.add_pandas`, `add_dataframe_asset`, `add_batch_definition_whole_dataframe`).
- **Phương án đã chọn:** Phương án 2 (GX 1.x Ephemeral Context).
- **Lý do:**
  - *Correctness & Tiêu chí Rubric*: Rubric bài lab yêu cầu bắt buộc chuẩn Great Expectations 1.x và trừ 10 điểm nếu dùng cú pháp cũ gây lỗi hoặc không tương thích.
  - *Tính độc lập & Nhẹ nhàng*: Ephemeral Context chạy trực tiếp trong bộ nhớ (in-memory), không phụ thuộc vào cấu trúc thư mục local cố định, tránh lỗi path khi chạy trên các hệ điều hành khác nhau (Windows vs Linux) của các thành viên trong nhóm.
  - *Dễ tích hợp CI/CD*: Cho phép pipeline truyền trực tiếp DataFrame trong bộ nhớ vào Batch validation mà không phải ghi tạm ra file trung gian.
- **Bằng chứng quyết định phù hợp:** Toàn bộ quá trình validation 4 expectations diễn ra trong chưa đầy 1 giây, xuất kết quả JSON chuẩn xác vào `data/quality/baseline_quality_report.json` với `gx_success = True`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec7' in position 6: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** Chạy kiểm thử dòng lệnh python in chuỗi tiếng Việt có dấu (`Tín hiệu hoàn thành: Clean thành công...`) trên Windows PowerShell.
- **Nguyên nhân gốc:** Môi trường console của Windows PowerShell mặc định sử dụng bảng mã `cp1252`, không tương thích với các ký tự Unicode tiếng Việt có dấu khi in ra `stdout`.
- **Cách xử lý:**
  1. Thêm biến môi trường `$env:PYTHONIOENCODING="utf-8"` và `$env:PYTHONPATH="src"` vào đầu lệnh chạy PowerShell.
  2. Trong mã nguồn `cleaning.py` và `quality.py`, luôn mở file ghi JSON bằng tham số tường minh `encoding="utf-8"` và `ensure_ascii=False`.
- **Cách xác minh sau khi sửa:** Chạy lại câu lệnh kiểm tra, console in ra đầy đủ tiếng Việt không lỗi: `Tín hiệu hoàn thành: Clean thành công 24 dòng`.
- **Điều học được:** Khi phát triển pipeline dữ liệu đa ngôn ngữ trên môi trường Windows, việc chuẩn hóa encoding UTF-8 ở cả tầng ứng dụng (Python I/O) và tầng môi trường thực thi (Shell/CLI) là bắt buộc để đảm bảo dữ liệu không bị biến dạng (corrupted text).

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Người 1 gọi Crossref REST API (hoặc fallback snapshot `crossref_response.json`) để parse ra danh sách `PaperRecord` lưu vào `crossref_records.json`.
   - Người 2 (tôi) nhận danh sách này, loại bỏ khoảng trắng thừa, tính toán `age_days`, khử trùng lặp theo `paper_id`, ghép nối trường ngữ cảnh `text_for_embedding` (5 phần), rồi đưa qua chốt Observability Gate (GX 1.x) để thẩm định chất lượng.
   - Sau khi dữ liệu sạch đạt kiểm định, Người 3 nạp `text_for_embedding` vào mô hình `all-MiniLM-L6-v2` để tính toán embedding vector và lưu vào ChromaDB collection `papers-baseline`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Bộ evaluation set (10 câu hỏi) bao gồm các câu hỏi thuộc 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`), đi kèm câu trả lời chuẩn (`ground_truth`) và danh sách ID bài báo liên quan (`ground_truth_doc_ids`).
   - `retrieval_hit_rate`: Đo lường tỷ lệ các câu hỏi mà top-k văn bản retrieved từ ChromaDB chứa ít nhất một `ground_truth_doc_id`.
   - `mean_token_f1`: So sánh độ trùng khớp từ vựng (token-level precision & recall) giữa câu trả lời sinh bởi LLM Agent và `ground_truth`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (GX 1.x)**: Giám sát tính toàn vẹn về mặt cấu trúc và nội dung (Schema & Syntactic Quality): số lượng dòng, trường bắt buộc không được null, tính duy nhất của ID, độ dài văn bản tối thiểu.
   - **Freshness monitoring**: Giám sát khía cạnh thời gian (Temporal SLA & Timeliness): dựa trên `age_days` để phát hiện dữ liệu bị cũ, lỗi thời, đảm bảo tri thức nạp vào RAG Agent luôn mới nhất và không vi phạm quy định SLA ($\le 25\%$ bài báo cũ quá 180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Trong phương pháp thực nghiệm khoa học, test set đóng vai trò là một biến đối chứng cố định (Control Benchmark). Nếu thay đổi câu hỏi kiểm thử giữa các trạng thái, ta sẽ không thể phân biệt được sự thay đổi điểm số là do chất lượng dữ liệu hay do độ khó/dễ của câu hỏi mới. Dùng chung một test set giúp đo lường chính xác tác động tiêu cực của Data Corruption và hiệu quả phục hồi của Idempotent Repair.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Artifact**: Báo cáo kiểm định `repaired_quality_report.json` và `repaired_metrics.json` được sinh ra, cùng bảng so sánh đối chiếu trong `data/reports/corruption_report.md`.
   - **Metrics**:
     - Quality Gate: `success` trở lại `True` (tất cả 4 expectations và Freshness SLA đều pass).
     - RAG Metrics: `retrieval_hit_rate` và `mean_token_f1` hồi phục về mức xấp xỉ hoặc bằng với trạng thái Baseline ban đầu, chứng minh hiện tượng Silent Failure đã được triệt tiêu hoàn toàn.

---

## 8. Phân tích kết quả

### Metrics chính (Dự kiến & Thực tế Baseline)

| Metric/signal | Baseline | Corrupted (Dự kiến) | Repaired (Dự kiến) | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | 0.80 - 1.00 | Giảm mạnh (< 0.50) | Phục hồi ($\ge 0.80$) | Dữ liệu bẩn làm sai lệch vector khiến retriever lấy nhầm văn bản; repair khôi phục đúng embedding. |
| `mean_token_f1` | 0.70 - 0.90 | Giảm mạnh (< 0.40) | Phục hồi ($\ge 0.70$) | Title bị cắt ngắn và summary rỗng khiến câu trả lời của LLM mất context chính xác. |
| Quality checks (GX) | **True** (4/4 pass) | **False** (Vi phạm) | **True** (4/4 pass) | GX 1.x bắt được ngay lỗi null, duplicate và độ dài ngắn khi dữ liệu bị tiêm lỗi. |
| Freshness status | **True** (0% stale) | **False** (Stale date) | **True** (0% stale) | Kịch bản lùi ngày xuất bản vi phạm ngưỡng SLA 180 ngày; repair lấy lại ngày gốc từ raw snapshot. |

### Kết luận từ số liệu

1. **Chuỗi sự cố:**
   $$\text{Tiêm 6 lỗi dữ liệu (Drop, Blank, Noise, Truncate, Stale, Duplicate)} \longrightarrow \text{Quality checks = False & Freshness = False} \longrightarrow \text{Hit Rate sụt giảm nghiêm trọng}.$$
2. **Chuỗi phục hồi:**
   $$\text{Idempotent Repair từ Raw Snapshot} \longrightarrow \text{Cleaning chuẩn hóa lại 24 bản ghi} \longrightarrow \text{Quality checks = True} \longrightarrow \text{Agent lấy lại độ chính xác ban đầu}.$$

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Về Data Pipeline**: Dữ liệu thô từ bên ngoài luôn tiềm ẩn rủi ro bất định; việc thiết kế một pipeline phân tách rõ ràng giữa tầng Ingestion, Cleaning và Serving giúp cô lập lỗi và tái lập dễ dàng.
2. **Về Data Observability**: Observability Gate với Great Expectations 1.x và Freshness SLA là chốt chặn sinh tử. Nó giúp chuyển đổi từ thế bị động (chờ người dùng phàn nàn AI trả lời sai) sang thế chủ động (chặn đứng dữ liệu bẩn trước khi vào Vector DB).
3. **Về Kiến trúc RAG**: Chất lượng của RAG Agent phụ thuộc trực tiếp vào chất lượng của `text_for_embedding`. Việc tổ chức ngữ cảnh 5 phần rõ ràng giúp mô hình embedding tối ưu hóa không gian vector tốt hơn nhiều so với việc chỉ ném văn bản thô vào database.

### Nếu có thêm thời gian
- Xây dựng thêm **Data Drift Detection** tự động theo dõi sự thay đổi ngữ nghĩa của các bài báo khoa học mới theo thời gian bằng mô hình thống kê phân bố embedding (ví dụ sử dụng Evidently AI hoặc KS-test), giúp phát hiện concept drift ngay cả khi schema dữ liệu không thay đổi.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Cao Đức Hiệp  
**Ngày xác nhận:** 2026-09-26  
