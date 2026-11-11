# Ghi chú phân tích · Day 04

Họ và tên: Trinh Tuan Phong
MSSV: 2A202603781

## 0. Lộ trình và yêu cầu

### Tiến độ theo GUIDE.md / CHECKPOINTS.md

| Bài | Yêu cầu chính | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1. Agent loop | `run_agent`: gọi model, giữ assistant message, thực thi mọi tool call, trả tool result đúng `tool_call_id`, dừng đúng, trace/usage | Đã xong | `python -m unittest tests.test_lab -v` → 12/12 pass; `run.py` CP2: `completed`, 4 model calls, tools `get_status` ×2 + `get_incident_details` ×3, steps 1–4 |
| 2. Lỗi và trace | `max_steps`, invalid JSON, tool/provider error, timeout, `finish=length`, trace đủ để debug | Đã xong (11/11/2026) | 37 test: 35 pass, 2 fail là `EvidenceGateTests` của Bài 4; probe lỗi + trace thật bên dưới |
| 3. Eval lần 1 | `evals/run_evals.py --output eval_before.json`, đủ 22 case, điểm tổng khác `null` | Chưa làm | |
| 4. Phân tích và cải tiến | Chọn case lỗi, ghi evidence vào mục 1–3, implement một cải tiến + validation nguồn, tests | Chưa làm | |
| 5. Eval lần 2 | Chạy `eval_after.json` cùng cấu hình, so sánh, điền mục 4–5 | Chưa làm | |
| Bonus (tuỳ chọn) | 5 status tools, pagination, 10 case, `eval_bonus.json` | Chưa làm | |

### Checkpoint (CHECKPOINTS.md)

| CP | Nội dung | Trạng thái | Bằng chứng |
|---|---|---|---|
| CP1 | Setup, khám phá tools | Đã xong | Repo đúng tên, `.env` có provider/model/key; hai tool chạy offline trên snapshot 2026-11-09T03:50Z |
| CP2 | Bài 1: agent loop | Đã xong | `test_lab` 12/12; `run.py` câu hỏi GitHub Actions → `completed`, 4 model calls, 5 tool calls |
| CP3 | Bài 2: lỗi và trace | Đã xong | 35/37 pass (2 fail Bài 4); các probe `INVALID_ARGUMENTS`, timeout, `length`, `max_steps`, malformed reply |
| CP4 | Bài 3: eval lần 1 | Chưa làm | Sẽ chạy `python evals/run_evals.py --output eval_before.json` |
| CP5 | Bài 4: phân tích, cải tiến | Chưa làm | Còn 2 test `EvidenceGateTests` chờ làm |
| CP6 | Bài 5: eval lần 2 | Chưa làm | |
| CP7 | Demo, chốt bài, nộp | Chưa làm | |

- Sau Bài 2, `python -m unittest discover -s tests -v` còn **2 test fail** trong `tests/test_validation.py` (`EvidenceGateTests`), thuộc Bài 4 — cố ý chưa làm để giữ `eval_before`/`eval_after`.
- PowerShell nếu in lỗi tiếng Việt: đặt `$env:PYTHONIOENCODING='utf-8'` trước khi chạy, hoặc dùng Git Bash.

### Bài 2 — Kiểm soát lỗi và trace (CP3)

**Kết quả audit:** `agent.py` đã có phần lớn yêu cầu Bài 2 từ lần làm Bài 1; nhiệm vụ Bài 2 là rà soát, vá lỗ hổng malformed reply, thêm test hồi quy và kiểm chứng lại. Contract `run_agent(question, provider, tools, max_steps=6)` và trace tool event giữ nguyên.

| # | Yêu cầu (GUIDE.md Bài 2) | Cách làm trong `agent.py` | Kiểm chứng |
|---|---|---|---|
| 1 | Giới hạn model calls bằng `max_steps`; hết lượt trả `max_steps` | Vòng `for step in range(1, max_steps + 1)`; sau vòng trả `status='max_steps'`, `error='MAX_STEPS: n'` | `test_max_steps`; probe `max_steps=1` |
| 2 | JSON arguments lỗi → tool result `INVALID_ARGUMENTS`, không crash | `_parse_arguments` trả `None`; result `{ok:false, error:'INVALID_ARGUMENTS'}` được append với đúng `tool_call_id` | `test_invalid_json_sent_back_to_model`; probe |
| 3 | Tool không tồn tại, timeout, provider lỗi → trace, cho model cơ hội | `_execute_tool` bắt `Exception`; `StatusTools.execute` trả `UNKNOWN_TOOL`/`TimeoutError`; provider exception → terminal error | `test_errors_are_observations`; `test_partial_timeout_does_not_affect_github`; probe provider/tool exception |
| 4 | `finish == 'length'` hoặc provider lỗi → `error`, không `completed` | Kiểm tra `length` trước khi chạy tool; trả `MODEL_OUTPUT_TRUNCATED`; provider exception trả `error` | `test_model_truncation_is_not_completed`; probe |
| 5 | Trace đủ debug, đúng format | Mọi item có `event`; tool event đúng 5 key; error event có `step`/`message`; không chain-of-thought, không key | trace CP2 thật; probe lỗi |

**Phân loại lỗi:**

| Nhóm | Ví dụ | Hành vi | `status` |
|---|---|---|---|
| Observation (tiếp tục loop) | `INVALID_ARGUMENTS`, `UNKNOWN_TOOL`, `TimeoutError` của tool, tool exception, `INCIDENT_NOT_FOUND` | Gửi tool result lại model để model tự sửa/báo thiếu dữ liệu | tiếp tục |
| Terminal (dừng run) | provider exception/HTTP/timeout, reply malformed, `finish='length'`, `finish` lạ không có calls | Ghi `event='error'`, trả `error` | `error` |
| Budget | Hết `max_steps` | Dừng, giữ partial answer để debug | `max_steps` |

**Lỗi phát hiện và đã sửa:**

- Trước khi sửa, nếu provider trả `calls` là dict hoặc phần tử không phải dict, loop crash `AttributeError: 'str' object has no attribute 'get'`.
- Đã thêm `_valid_calls` trong `agent.py`: chỉ chấp nhận list call là dict có `id`/`name` là chuỗi không rỗng. Reply sai contract trả `status='error'`, `error='MALFORMED_PROVIDER_REPLY'`, trace có `event='error'`; không gửi history chứa `tool_call_id=None` cho provider.
- Đã kiểm chứng bằng probe offline: `calls` là dict → `status='error'`, `error='MALFORMED_PROVIDER_REPLY'`, trace có `event='error'`; provider raise `TimeoutError` → `error` + trace.

**Trace mẫu (probe thật):**

```json
[
  {"event": "step", "step": 1, "finish": "tool_calls"},
  {"event": "tool", "step": 1, "name": "get_status",
   "arguments": {"provider": "cloudflare"},
   "result": {"ok": false, "error": "TimeoutError", "message": "Cloudflare status timeout (eval giả lập)."}}
]
```

```json
[
  {"event": "step", "step": 1, "finish": "tool_calls"},
  {"event": "error", "step": 1, "message": "Provider trả calls không hợp lệ (cần list call có id/name)."}
]
```

**Lệnh đã chạy và kết quả thật:**

```text
python -m unittest tests.test_lab -v        -> Ran 12 tests, OK
python -m unittest discover -s tests        -> Ran 37 tests, FAILED (failures=2)
  (2 fail: EvidenceGateTests.test_missing_url_gets_revision_within_budget,
           EvidenceGateTests.test_missing_url_at_budget_limit_is_not_completed — Bài 4)
python run.py 'GitHub Actions hiện có sự cố không? Hãy kiểm tra incident gần đây.'
  -> status=completed, 4 model calls, tools: get_status ×2, get_incident_details ×3, steps 1–4
```

Probe lỗi (offline, dùng `FakeProvider`/`ScenarioTools`):

| Probe | Kết quả |
|---|---|
| JSON `{` | `completed`; tool result `INVALID_ARGUMENTS` |
| Cloudflare timeout | `completed`; tool result `TimeoutError` |
| `finish='length'` | `error`; `MODEL_OUTPUT_TRUNCATED` |
| `max_steps=1` + tool call | `max_steps`; `MAX_STEPS: 1` |
| `calls` là dict | `error`; `MALFORMED_PROVIDER_REPLY`, có trace error |
| provider raise `TimeoutError` | `error`; trace `event='error'` |

**Giới hạn của phần này:**

- Test offline dùng `FakeProvider`, không chứng minh agent trả lời đúng ngoài thực tế; chỉ chứng minh contract và đường xử lý lỗi.
- Lỗi provider có thể kết thúc run (đúng GUIDE); chỉ lỗi tool mới được trả làm observation.
- Tool calls ở bước cuối vẫn được thực thi (tool chỉ đọc) rồi trả `max_steps`; không có model call thêm.
- Trace cố ý không chứa chain-of-thought; message lỗi cắt 200 ký tự; không chứa key.
- Reply malformed bị dừng thay vì retry vì history sẽ không hợp lệ với provider.
- 2 test `EvidenceGateTests` vẫn fail có chủ đích cho đến CP5/Bài 4.

### Việc tiếp theo (CP4 — Bài 3)

- Chạy `python evals/run_evals.py --output eval_before.json` với đúng provider/model/max_steps đã dùng, kiểm tra `summary.score_0_100` khác `null` và đủ 22 case.
- Đọc `summary`, `grade.reason`, `grade.mechanical`, answer và trace; chọn case lỗi cho Bài 4.
- Chưa chạy trong bước Bài 2 này.

### Yêu cầu nộp bài (SUBMISSION.md)

- [ ] `python -m unittest discover -s tests -v` không còn test lỗi. (Hiện còn 2 test `EvidenceGateTests` của Bài 4; sẽ xong ở CP5.)
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
