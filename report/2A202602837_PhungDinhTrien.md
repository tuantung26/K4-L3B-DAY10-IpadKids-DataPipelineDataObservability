# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phùng Đình Triển             |
| MSSV               | 2A202602837                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | IpadKits     |
| Vai trò chính    | Data Ingestion (Crossref API) & Data Corruption Simulation |
| Repository         | https://github.com/tuantung26/K4-L3B-DAY10-IpadKids-DataPipelineDataObservability.git |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Thu thập & lưu trữ dữ liệu gốc (Bước 2) | `src/ingestion/crossref.py` — `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Query/filter từ `Settings` (`source_query`, `source_filter`, `max_results=24`) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 bài báo) | Hoàn thành |
| Mô phỏng lỗi dữ liệu thực nghiệm (Bước 7) | `src/ingestion/corruption.py` — `corrupt_clean_dataframe` | `clean_df` (24 dòng, từ `data/clean/papers_clean.csv` — Bước 3) | DataFrame đã corrupt (22 dòng) + `data/results/corruption_log.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Debug lỗi `KeyError: 'categories'`/`'categories_joined'` khi ChromaDB tự động loại bỏ metadata key có giá trị null | `src/retrieval/qa.py` — module `answer_question` (Bước 6, 8) | Sửa `_extract_answer` dùng `.get()` an toàn kèm kiểm tra NaN, giúp `run_phase1.py` và `run_corruption_flow.py` chạy được hết pipeline mà không crash |
| Debug lỗi model Gemini bị deprecated (`gemini-2.5-flash` 404 NOT_FOUND) chặn `evaluate_pipeline` | `src/evaluation/metrics.py` — hàm `_judge_answer` (Bước 6, 8) | Xác định nguyên nhân do model bị Google ngừng hỗ trợ, hướng dẫn đổi `LLM_MODEL` trong `.env` để pipeline chạy tiếp |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Gọi Crossref API (có retry + fallback offline), parse payload, lưu raw + records | `src/ingestion/crossref.py` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 bài báo) | `python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s)"` → in ra "Tín hiệu hoàn thành: Đã tải 24 bài báo" |
| Tiêm 6 dạng lỗi dữ liệu thực tế vào clean_df và ghi log chi tiết | `src/ingestion/corruption.py` | `data/results/corruption_log.json` (24 → 22 dòng, đủ 6 loại lỗi với DOI cụ thể) | `python .\script\run_corruption_flow.py` → tạo `data/reports/corruption_report.md`, cho thấy Corrupted làm Quality Gate FAIL và Retrieval Hit Rate giảm còn 60% |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`data/results/corruption_log.json` ghi lại chính xác 24 → 22 bản ghi sau corrupt (4 DOI bị drop, 3 blank summary, 3 inject noise, 3 truncate title, 3 stale date, 2 duplicate). Dữ liệu này là input trực tiếp làm `run_corruption_flow_pipeline` phát hiện Quality Gate chuyển từ PASS sang **FAIL** (do vi phạm `ExpectColumnValuesToBeUnique` và `ExpectColumnValueLengthsToBeBetween`) và Retrieval Hit Rate sụt từ 100% xuống **60%** — chứng minh corruption của tôi mô phỏng đủ nghiêm trọng để tạo ra "Silent Failure" thực sự trên RAG agent, đúng mục tiêu bài lab.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi giải quyết hai vấn đề trong pipeline: (1) thu thập dữ liệu nguồn từ Crossref API một cách ổn định, có khả năng phục hồi khi API lỗi (rate limit, mất mạng), đồng thời cất giữ bản gốc phục vụ Data Lineage; (2) mô phỏng các lỗi dữ liệu thực tế thường gặp trong pipeline sản xuất (thiếu dữ liệu, nhiễu, sai định dạng, dữ liệu cũ, trùng lặp) để tạo bộ dữ liệu kiểm thử cho Data Observability, làm bằng chứng cho hiện tượng Silent Failure ở Bước 8.

### Cách triển khai

- `fetch_source_records`: gọi Crossref REST API với retry có backoff tuyến tính cho các mã lỗi tạm thời (429, 500, 502, 503, 504), tối đa 3 lần thử. Nếu vẫn thất bại hoàn toàn, tự động fallback đọc lại snapshot JSON đã lưu trước đó (`data/raw/crossref_response.json`) thay vì làm gián đoạn pipeline.
- `parse_crossref_payload`: chuẩn hóa cấu trúc JSON lồng nhau của Crossref — bóc DOI, title, abstract (loại bỏ thẻ JATS/XML rác bằng regex), tác giả (ghép given + family), subject, và chuyển `date-parts` dạng `[[year, month, day]]` sang chuỗi ISO — đồng thời loại bỏ record thiếu trường bắt buộc (DOI/title/abstract).
- `corrupt_clean_dataframe`: dùng `random.Random(seed cố định)` để đảm bảo kết quả corrupt tái lập được giữa các lần chạy. Áp dụng tuần tự 6 phép biến đổi (drop 20% latest, blank summary, inject noise, truncate title, stale date, duplicate rows) lên các tập con ngẫu nhiên của dữ liệu, sau đó rebuild lại cột `text_for_embedding` để phản ánh đúng dữ liệu đã bị hỏng, và ghi log chi tiết DOI nào bị loại lỗi nào ảnh hưởng — log này chính là cơ sở để `repair_from_raw_snapshot` biết cần phục hồi từ snapshot gốc.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `Settings` (query/filter Crossref, `max_results=24`) cho Bước 2; `clean_df: pd.DataFrame` (24 dòng, schema gồm `paper_id`, `title`, `summary`, `authors`, `categories`, `published`, `age_days`, `text_for_embedding`...) cho Bước 7 |
| Output | List `PaperRecord` + 2 file JSON raw (Bước 2); `pd.DataFrame` đã corrupt (22 dòng, 16 cột) + `corruption_log.json` (Bước 7) |
| Module phụ thuộc | `core.config.Settings`; Bước 7 phụ thuộc trực tiếp vào output của Bước 3 (`build_clean_dataframe`) |
| Module sử dụng output | Bước 3 (`cleaning.py`) dùng output Bước 2; Bước 8 (`corruption_flow.py` — `run_corruption_flow_pipeline`, `repair_from_raw_snapshot`) dùng output Bước 7 để tạo `corrupted_df`, sau đó dùng `data/raw/crossref_records.json` (cũng do tôi tạo ra ở Bước 2) để phục hồi dữ liệu sạch |
| Điều kiện lỗi cần xử lý | API Crossref timeout/429/5xx (Bước 2, xử lý bằng retry + fallback); DataFrame rỗng đầu vào (Bước 7, raise `ValueError`) |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s)"
python .\script\run_corruption_flow.py
```

- **Kết quả mong đợi:** Bước 2 in ra "Tín hiệu hoàn thành: Đã tải 24 bài báo"; Bước 7-8 tạo được `data/results/corruption_log.json` và `data/reports/corruption_report.md` thể hiện rõ sự sụt giảm ở trạng thái Corrupted và phục hồi ở trạng thái Repaired.
- **Kết quả thực tế:** ✅ Đúng như mong đợi — 24 bài báo tải về; corruption làm 24 dòng còn 22 dòng; báo cáo cuối cùng cho thấy Retrieval Hit Rate giảm từ 100% (Baseline) xuống 60% (Corrupted) và phục hồi lại đúng 100% (Repaired).
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/results/corruption_log.json`, `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần đảm bảo hàm `corrupt_clean_dataframe` cho ra kết quả nhất quán giữa các lần chạy, để việc so sánh Baseline/Corrupted/Repaired ở Bước 8 có ý nghĩa và tái lập được.
- **Các phương án đã cân nhắc:** (1) Dùng `random` không seed — mỗi lần chạy corrupt các dòng khác nhau; (2) Dùng `random.Random(seed cố định)` — cố định chính xác tập dòng bị ảnh hưởng qua mọi lần chạy.
- **Phương án đã chọn:** Phương án 2 — seed cố định (`CORRUPTION_SEED = 42`).
- **Lý do:** Nếu không cố định seed, mỗi lần chạy lại pipeline sẽ corrupt các DOI khác nhau, khiến việc so sánh hiệu năng giữa các lần chạy không có ý nghĩa (không reproducible) và gây khó khăn khi debug hoặc đánh giá hiệu quả phục hồi ở Bước 8.
- **Bằng chứng quyết định phù hợp:** Báo cáo cuối cùng `corruption_report.md` cho thấy kết quả nhất quán, rõ ràng: Corrupted luôn vi phạm đúng 2 Expectation cụ thể (`ExpectColumnValuesToBeUnique`, `ExpectColumnValueLengthsToBeBetween`) — không đổi qua các lần chạy lại — chứng tỏ tính tái lập của corruption đã hoạt động đúng như thiết kế.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `KeyError: 'categories_joined'` tại `src/retrieval/qa.py`, dòng `return metadata["categories_joined"]`, xảy ra khi chạy `run_corruption_flow.py` trên dữ liệu đã corrupt (nhưng không xảy ra khi chạy trên dữ liệu Baseline sạch).
- **Lệnh hoặc bước tái hiện:** `python .\script\run_corruption_flow.py`, lỗi phát sinh ở bước 4 "Rebuilding index and evaluating on corrupted data".
- **Nguyên nhân gốc:** Sau khi `blank_summary`/corruption làm một số ô dữ liệu bị rỗng, khi đọc lại `clean_df` từ CSV bằng `pd.read_csv`, các ô rỗng bị pandas chuyển thành `NaN`. Khi `LocalEmbeddingIndex.build` gửi metadata (bao gồm giá trị `NaN`) lên ChromaDB, ChromaDB tự động loại bỏ hẳn key có giá trị `NaN` khỏi metadata lưu trữ — khiến lúc truy vấn lại, `metadata["categories_joined"]` không tồn tại nữa và gây `KeyError`.
- **Cách xử lý:** Sửa `_extract_answer` trong `qa.py` dùng `metadata.get(key)` thay vì index trực tiếp `metadata[key]`, kèm hàm `_safe_str()` kiểm tra rõ ràng cả trường hợp `None` và `float('nan')` (vì `NaN` là giá trị truthy trong Python nên `value or ""` không đủ để bắt được nó), trả về chuỗi rỗng an toàn thay vì crash.
- **Cách xác minh sau khi sửa:** Chạy lại `python .\script\run_corruption_flow.py` — pipeline chạy hết toàn bộ 8 bước, không còn `KeyError`, tạo ra `data/reports/corruption_report.md` hoàn chỉnh.
- **Điều học được:** Dữ liệu đi qua nhiều lần round-trip (DataFrame → CSV → DataFrame) có thể âm thầm đổi kiểu dữ liệu (chuỗi rỗng → NaN), và các hệ thống lưu trữ bên thứ ba (ChromaDB) có thể có hành vi ẩn (tự loại bỏ giá trị null) không được ghi rõ trong luồng chính — luôn nên truy cập dict/metadata bằng `.get()` có giá trị mặc định thay vì index trực tiếp khi dữ liệu đã từng đi qua một bước có khả năng làm hỏng (corruption) hoặc chuyển đổi định dạng.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Dữ liệu đi từ Crossref REST API (thu thập metadata: DOI, title, abstract, authors, ngày xuất bản) → làm sạch và chuẩn hóa, tính `age_days`, ghép các trường thành `text_for_embedding` (Bước 3) → sinh vector embedding bằng mô hình Sentence-Transformers (`all-MiniLM-L6-v2`) → nạp vào ChromaDB (vector database) để phục vụ truy vấn ngữ nghĩa cho hệ thống RAG (Bước 6).
2. Evaluation set gồm 10 câu hỏi thuộc 4 loại (summary/authors/date/categories), mỗi câu có `ground_truth` (đáp án chuẩn) và `ground_truth_doc_ids` (DOI tài liệu nguồn đúng) — dùng để: (a) so sánh câu trả lời hệ thống tạo ra với `ground_truth` bằng Token F1, và (b) kiểm tra xem tài liệu mà hệ thống truy xuất được (retrieval) có trùng với `ground_truth_doc_ids` hay không, từ đó tính Retrieval Hit Rate.
3. Quality checks (Great Expectations — kiểm tra số dòng, giá trị null, tính unique của `paper_id`, độ dài tối thiểu của `summary`) đánh giá **tính toàn vẹn cấu trúc** của dữ liệu tại một thời điểm cụ thể; trong khi Freshness Monitoring đánh giá riêng **tính "mới" theo thời gian** (tỷ lệ bài báo có `age_days > 180` ngày) — đây là hai khía cạnh độc lập của Data Observability. Số liệu thực tế cho thấy rõ điều này: ở trạng thái Corrupted, Quality Gate **FAIL** (do trùng lặp và độ dài summary) nhưng Freshness SLA vẫn **FRESH** (13.64% < ngưỡng 25%) — chứng minh 2 loại lỗi này độc lập với nhau.
4. Dùng cùng một test set cho cả 3 trạng thái (Baseline/Corrupted/Repaired) để đảm bảo phép so sánh công bằng — nếu mỗi trạng thái dùng bộ câu hỏi khác nhau, sự chênh lệch về metric có thể do độ khó câu hỏi khác nhau chứ không phản ánh đúng ảnh hưởng của việc dữ liệu bị hỏng hay được phục hồi.
5. Repair được coi là thành công dựa trên bằng chứng cụ thể: Quality Gate chuyển từ FAIL trở lại PASS (cả 4 Expectation đều pass), Freshness SLA duy trì FRESH, và quan trọng nhất là các metric agent phục hồi **chính xác về đúng mức Baseline ban đầu** (Retrieval Hit Rate 100%, Mean Token F1 0.8000, Judge Accuracy 80%, Mean Judge Score 4.20/5.0) — không chỉ "cải thiện" mà là khớp hoàn toàn với số liệu gốc.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 100.00% | 60.00% | 100.00% | Sụt giảm mạnh 40 điểm % khi dữ liệu bị hỏng, do title bị cắt ngắn và summary bị làm rỗng khiến vector embedding lệch hướng khỏi ground-truth doc |
| `mean_token_f1` | 0.8000 | 0.4000 | 0.8000 | Giảm đúng 50% — phản ánh trực tiếp việc noise/blank summary làm agent trả lời sai lệch hoặc rơi vào câu trả lời mặc định |
| `judge_accuracy` | 80.00% | 40.00% | 80.00% | Giảm cùng biên độ với Token F1, cho thấy LLM Judge và Token F1 nhất quán trong việc phát hiện suy giảm chất lượng |
| `mean_judge_score` | 4.20/5.0 | 2.60/5.0 | 4.20/5.0 | Điểm đánh giá giảm 1.6 điểm — mức giảm tương đối lớn cho thấy corruption ảnh hưởng nghiêm trọng đến chất lượng câu trả lời, không chỉ độ chính xác nhị phân |
| Quality checks (GX) | PASS | FAIL (2/4 expectation) | PASS | Đúng như thiết kế — `ExpectColumnValuesToBeUnique` fail do duplicate rows, `ExpectColumnValueLengthsToBeBetween` fail do blank/truncate summary |
| Freshness status | FRESH (0% stale) | FRESH (13.64% stale) | FRESH (0% stale) | Dù stale_ratio tăng lên ở Corrupted, vẫn chưa vượt ngưỡng 25% nên trạng thái tổng thể vẫn FRESH — cho thấy corruption của tôi tạo đủ nhiễu để ảnh hưởng Quality Gate nhưng chưa đủ mạnh để kích hoạt cảnh báo Freshness |

### Kết luận từ số liệu

1. **[Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:** Việc tiêm đồng thời `blank_summary`, `truncate_title` và `duplicate_rows` (Bước 7) làm Quality Gate chuyển từ PASS sang FAIL (vi phạm `ExpectColumnValuesToBeUnique` và `ExpectColumnValueLengthsToBeBetween`) → điều này kéo theo Retrieval Hit Rate giảm từ 100% xuống 60% và Mean Token F1 giảm một nửa (0.8 → 0.4), vì các bản ghi bị rỗng/trùng lặp làm vector embedding không còn phản ánh đúng nội dung gốc.
2. **[Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi]:** Hành động `repair_from_raw_snapshot` (đọc lại `data/raw/crossref_records.json` — chính là snapshot do tôi tạo ra ở Bước 2 — và chạy lại `build_clean_dataframe`) làm Quality Gate quay về PASS hoàn toàn → kéo theo toàn bộ 4 metric agent (Hit Rate, Token F1, Judge Accuracy, Judge Score) phục hồi về **chính xác** mức Baseline ban đầu, chứng minh Idempotent Repair từ Raw Snapshot hoạt động đúng thiết kế.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

`blank_summary` và `truncate_title` ảnh hưởng rõ nhất, vì `text_for_embedding` được ghép trực tiếp từ `title` và `summary` — khi 2 trường này bị rỗng/cắt ngắn, vector embedding sinh ra gần như mất hết ngữ nghĩa gốc, khiến việc truy xuất (retrieval) tìm sai tài liệu hoàn toàn thay vì chỉ trả lời kém chính xác hơn một chút. Đây là bằng chứng rõ cho khái niệm "Silent Failure" — hệ thống không báo lỗi runtime nào, chỉ âm thầm trả lời sai.

**Kết quả nào khác với kỳ vọng ban đầu?**

Tôi ban đầu dự đoán `stale_date` (dữ liệu cũ) sẽ ảnh hưởng nhiều đến Freshness SLA đến mức chuyển trạng thái sang STALE, nhưng thực tế `stale_ratio` ở Corrupted chỉ đạt 13.64% — chưa đủ vượt ngưỡng 25% để kích hoạt cảnh báo. Điều này cho thấy tỉ lệ corrupt tôi thiết lập (15% số dòng mỗi loại lỗi) tuy đủ mạnh để phá vỡ Quality Gate (dựa trên uniqueness/length) nhưng chưa đủ mạnh để phá vỡ Freshness SLA (dựa trên tỉ lệ phần trăm toàn tập dữ liệu) — hai ngưỡng kiểm định có độ nhạy khác nhau với cùng một cường độ corruption.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data Lineage (giữ lại bản gốc raw response ở Bước 2) là bước phòng ngừa quan trọng — nó không chỉ tránh phụ thuộc vào tính sẵn có tức thời của API, mà còn là chìa khóa cho phép `repair_from_raw_snapshot` phục hồi metrics về **chính xác** mức Baseline (không chỉ "gần đúng"), chứng minh giá trị thực tiễn của nguyên tắc Idempotent Repair.
2. Việc mô phỏng lỗi dữ liệu (corruption) cho thấy các loại Quality Gate khác nhau có độ nhạy khác nhau với cùng một cường độ lỗi — `ExpectColumnValuesToBeUnique`/`ExpectColumnValueLengthsToBeBetween` bị vi phạm ngay ở mức 15% corruption, trong khi Freshness SLA (ngưỡng 25%) vẫn chưa bị kích hoạt — nên khi thiết kế hệ thống giám sát thực tế, cần hiểu rõ ngưỡng nhạy cảm riêng của từng loại kiểm định thay vì giả định chúng phản ứng đồng đều.
3. Corruption ở tầng dữ liệu đầu vào (title/summary bị hỏng) gây ảnh hưởng nghiêm trọng hơn nhiều so với dự đoán trực giác lên RAG agent — Retrieval Hit Rate giảm 40 điểm % và Token F1 giảm 50% chỉ từ việc làm hỏng khoảng 15-20% bản ghi, cho thấy hệ thống RAG rất nhạy với chất lượng văn bản dùng để tạo embedding, và một tỉ lệ nhỏ dữ liệu bẩn có thể gây suy thoái không tương xứng (disproportionate) lên toàn bộ chất lượng hệ thống.

### Nếu có thêm thời gian

Tôi muốn mở rộng `corrupt_clean_dataframe` để hỗ trợ tham số điều chỉnh tỉ lệ corruption theo từng loại lỗi độc lập (hiện đang cố định 15-20%), sau đó chạy `run_corruption_flow_pipeline` ở nhiều mức cường độ khác nhau (ví dụ 5%, 10%, 15%, 20%, 30%) để vẽ được đường cong tương quan giữa % dữ liệu bị hỏng và mức độ suy giảm Retrieval Hit Rate/Token F1 — từ đó xác định chính xác "ngưỡng chịu đựng" (breaking point) của hệ thống RAG trước khi Silent Failure trở nên nghiêm trọng, đo bằng cách so sánh độ dốc suy giảm giữa các mức cường độ.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phùng Đình Triển
**Ngày xác nhận:** 2026-09-26