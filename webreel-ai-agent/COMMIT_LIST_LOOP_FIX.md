# Danh Sách File Cần Commit - Loop Detection Fix

Tài liệu này liệt kê các file cần commit cho tính năng phát hiện và xử lý vòng lặp trong OS Recorder.

## Ngày: 2 tháng 4, 2026

## Nhánh làm việc
- Nhánh hiện tại: `dev/ai-agent-video-tutor/nguyen-van-tong`
- Nhánh đích: `ai-agent-video-tutor` (sau khi merge)

## Mô tả thay đổi

Tích hợp cơ chế phát hiện và xử lý vòng lặp vào OS Recorder pipeline v3 dual output, bao gồm:
- Phát hiện vòng lặp dựa trên lịch sử hành động và trạng thái màn hình
- Xử lý vòng lặp với các chiến lược khác nhau (retry, skip, alternative)
- Tích hợp vào planning agent v2 và executor v2
- Cải thiện trace composer để hỗ trợ loop detection

## Danh sách file cần commit

### 1. Core Python files trong os_recorder

<table>
<tr>
<th>File</th>
<th>Mô tả thay đổi</th>
<th>Loại commit</th>
</tr>
<tr>
<td>webreel-ai-agent/src/webreel_runner.py</td>
<td>Cập nhật runner để hỗ trợ loop detection</td>
<td>feat</td>
</tr>
<tr>
<td>webreel-ai-agent/os_recorder/core/os_planning_agent_v2.py</td>
<td>Tích hợp loop detection vào planning agent</td>
<td>feat</td>
</tr>
<tr>
<td>webreel-ai-agent/os_recorder/core/os_executor_v2.py</td>
<td>Thêm xử lý vòng lặp trong executor</td>
<td>feat</td>
</tr>
<tr>
<td>webreel-ai-agent/os_recorder/core/trace_composer.py</td>
<td>Cải thiện trace composer cho loop detection</td>
<td>feat</td>
</tr>
<tr>
<td>webreel-ai-agent/os_recorder/core/excel_engine.py</td>
<td>Cập nhật excel engine để tương thích với loop detection</td>
<td>fix</td>
</tr>
</table>

### 2. Documentation files

<table>
<tr>
<th>File</th>
<th>Mô tả</th>
<th>Loại commit</th>
</tr>
<tr>
<td>webreel-ai-agent/os_recorder/LOOP_DETECTION_FIX.md</td>
<td>Tài liệu chi tiết về cơ chế loop detection</td>
<td>docs</td>
</tr>
<tr>
<td>webreel-ai-agent/os_recorder/CHANGELOG_LOOP_FIX.md</td>
<td>Changelog cho tính năng loop detection</td>
<td>docs</td>
</tr>
</table>

### 3. Test files

<table>
<tr>
<th>File</th>
<th>Mô tả</th>
<th>Loại commit</th>
</tr>
<tr>
<td>webreel-ai-agent/os_recorder/test_loop_detection.py</td>
<td>Test script cho loop detection</td>
<td>test</td>
</tr>
</table>

## Quy trình commit

### Bước 1: Commit code changes (feat)

```bash
# Đảm bảo đang ở nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong

# Thêm các file Python core
git add webreel-ai-agent/src/webreel_runner.py
git add webreel-ai-agent/os_recorder/core/os_planning_agent_v2.py
git add webreel-ai-agent/os_recorder/core/os_executor_v2.py
git add webreel-ai-agent/os_recorder/core/trace_composer.py

# Commit với message feat
git commit -m "feat: add loop detection mechanism to OS Recorder pipeline v3"
```

### Bước 2: Commit bug fix (fix)

```bash
# Thêm file excel_engine fix
git add webreel-ai-agent/os_recorder/core/excel_engine.py

# Commit với message fix
git commit -m "fix: update excel engine for loop detection compatibility"
```

### Bước 3: Commit documentation (docs)

```bash
# Thêm các file documentation
git add webreel-ai-agent/os_recorder/LOOP_DETECTION_FIX.md
git add webreel-ai-agent/os_recorder/CHANGELOG_LOOP_FIX.md

# Commit với message docs
git commit -m "docs: add loop detection documentation and changelog"
```

### Bước 4: Commit test files (test)

```bash
# Thêm test script
git add webreel-ai-agent/os_recorder/test_loop_detection.py

# Commit với message test
git commit -m "test: add loop detection test script"
```

### Bước 5: Push nhánh dev (optional, để backup)

```bash
git push mentor dev/ai-agent-video-tutor/nguyen-van-tong
```

### Bước 6: Merge vào nhánh project

```bash
# Chuyển về nhánh project
git checkout ai-agent-video-tutor

# Pull để đảm bảo nhánh mới nhất
git pull mentor ai-agent-video-tutor

# Merge từ dev
git merge dev/ai-agent-video-tutor/nguyen-van-tong

# Push để mentor review
git push mentor ai-agent-video-tutor
```

### Bước 7: Quay lại nhánh dev

```bash
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
```

## Checklist trước khi commit

- [ ] Đã kiểm tra nhánh hiện tại là dev branch
- [ ] Đã test loop detection với các test cases
- [ ] Đã loại bỏ file test output, cache không cần thiết
- [ ] Commit message có prefix đúng (feat/fix/docs/test)
- [ ] Commit message ngắn gọn, rõ ràng, không có emoji
- [ ] Đã review lại các file sẽ commit bằng `git status`

## Checklist trước khi merge

- [ ] Đã commit tất cả thay đổi trên nhánh dev
- [ ] Đã test đầy đủ loop detection với Excel, Word, PowerPoint
- [ ] Đã cập nhật tài liệu LOOP_DETECTION_FIX.md và CHANGELOG_LOOP_FIX.md
- [ ] Đã pull nhánh project mới nhất trước khi merge
- [ ] Đã kiểm tra không có conflict
- [ ] Đã review lại toàn bộ thay đổi sẽ merge

## Tóm tắt thay đổi

Tính năng loop detection được tích hợp vào OS Recorder pipeline v3 dual output với các cải tiến chính:

1. Phát hiện vòng lặp dựa trên:
   - Lịch sử hành động (action history)
   - Trạng thái màn hình (screenshot similarity)
   - Kết quả thực thi (execution results)

2. Xử lý vòng lặp với các chiến lược:
   - Retry với tham số khác
   - Skip action hiện tại
   - Thử alternative action
   - Abort nếu vượt quá threshold

3. Tích hợp vào các module:
   - Planning Agent v2: Phát hiện loop trong quá trình planning
   - Executor v2: Xử lý loop trong quá trình execution
   - Trace Composer: Ghi nhận loop events vào trace

4. Test coverage:
   - Test với Excel automation
   - Test với Word document
   - Test với PowerPoint presentation

## Lưu ý

- Không commit các file trong `.webreel/` (output videos, timelines)
- Không commit các file trong `workspace/` (test outputs)
- Không commit các file `.env` hoặc API keys
- Không commit các file binary không cần thiết
