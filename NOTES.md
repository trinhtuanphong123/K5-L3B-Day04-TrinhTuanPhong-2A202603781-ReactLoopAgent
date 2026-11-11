# Ghi chú phân tích · Day 04

Họ và tên: Trinh Tuan Phong
MSSV: 2A202603781

## 0. Lộ trình và yêu cầu

### Tiến độ theo GUIDE.md / CHECKPOINTS.md

| Bài | Yêu cầu chính | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1. Agent loop | `run_agent`: gọi model, giữ assistant message, thực thi mọi tool call, trả tool result đúng `tool_call_id`, dừng đúng, trace/usage | Đã xong | `python -m unittest tests.test_lab -v` → 12/12 pass; CP2 qua `run.run`: `completed`, tools `get_status`, `get_incident_details` ×2, 3 model calls |
| 2. Lỗi và trace | `max_steps`, invalid JSON, tool/provider error, timeout, `finish=length`, trace đủ để debug | Chưa làm | |
| 3. Eval lần 1 | `evals/run_evals.py --output eval_before.json`, đủ 22 case, điểm tổng khác `null` | Chưa làm | |
| 4. Phân tích và cải tiến | Chọn case lỗi, ghi evidence vào mục 1–3, implement một cải tiến + validation nguồn, tests | Chưa làm | |
| 5. Eval lần 2 | Chạy `eval_after.json` cùng cấu hình, so sánh, điền mục 4–5 | Chưa làm | |
| Bonus (tuỳ chọn) | 5 status tools, pagination, 10 case, `eval_bonus.json` | Chưa làm | |

- Sau Bài 1, `python -m unittest discover -s tests -v` còn **2 test fail** trong `tests/test_validation.py` (`EvidenceGateTests`), thuộc Bài 4 — cố ý chưa làm để giữ `eval_before`/`eval_after`.
- PowerShell nếu in lỗi tiếng Việt: đặt `$env:PYTHONIOENCODING='utf-8'` trước khi chạy, hoặc dùng Git Bash.

### Yêu cầu nộp bài (SUBMISSION.md)

- [ ] `python -m unittest discover -s tests -v` không còn test lỗi.
- [ ] `eval_before.json` và `eval_after.json` cùng agent model, judge model, snapshot, max steps, dataset; đủ 22 case; điểm tổng khác `null`.
- [ ] `NOTES.md` đủ 5 mục (1–5).
- [ ] Không có `.env` hay API key; `git ls-files | grep .env` chỉ thấy `.env.example`.
- [ ] Tên repo đúng quy ước, public, đã dán link lên LMS.
- [ ] Bonus (nếu làm): nộp thêm `eval_bonus.json`.

### Quy tắc bắt buộc (RULES.md / RUBRIC.md)

- Không dùng LangChain, LangGraph hay framework agent khác.
- Không sửa `fixtures/`, `evals/cases.json`, `evals/scenarios.py`, `evals/grading.py` hay rubric.
- `NOTES.md` dựa trên trace thật; không chép code/notes của người khác.
- Không commit `.env` hay API key.

## 1. Case được chọn

- ID case:
- Câu trả lời của agent:
- Điểm ở lần chạy 1:

## 2. Bằng chứng trong trace

Dán đoạn trace chứng minh lỗi và nêu nguyên nhân có thể xảy ra.

```text

```

## 3. Thay đổi đã thực hiện

- Sửa gì, ở đâu:
- Vì sao chọn thay đổi này:

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng |  |  |
| Điểm case đã chọn |  |  |
| Số model calls |  |  |
| Token, chi phí nếu có |  |  |

- Lỗi đã giải quyết:
- Lỗi còn lại hoặc mới xuất hiện:

## 5. Giới hạn

Nêu giới hạn của điểm judge, của snapshot và của việc chỉ chạy một lần mỗi phiên bản.
