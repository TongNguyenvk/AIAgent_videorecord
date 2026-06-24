# Quy trình Git và Commit Convention

Tài liệu này mô tả chi tiết quy trình làm việc với Git và quy tắc commit message theo yêu cầu của mentor.

## 1. Chiến lược phân nhánh (Branching Strategy)

### Cấu trúc nhánh

<table>
<tr>
<th>Nhánh</th>
<th>Mục đích</th>
<th>Quy tắc</th>
</tr>
<tr>
<td>main</td>
<td>Chỉ chứa tài liệu tổng quan và hướng dẫn</td>
<td>Nghiêm cấm code trực tiếp</td>
</tr>
<tr>
<td>project/[ten-du-an]</td>
<td>Nhánh gốc của từng dự án</td>
<td>Nhánh chính cho dự án, merge từ dev branches</td>
</tr>
<tr>
<td>dev/[ten-du-an]/[ten-sinh-vien]</td>
<td>Nhánh làm việc hàng ngày của sinh viên</td>
<td>Nhánh cá nhân để phát triển tính năng</td>
</tr>
</table>

### Áp dụng cho dự án AI Agent Video Tutor

<table>
<tr>
<th>Nhánh</th>
<th>Mục đích</th>
</tr>
<tr>
<td>ai-agent-video-tutor</td>
<td>Nhánh project chính, mentor review tại đây</td>
</tr>
<tr>
<td>dev/ai-agent-video-tutor/nguyen-van-tong</td>
<td>Nhánh làm việc hàng ngày của sinh viên</td>
</tr>
</table>

Lưu ý: Theo cấu trúc thực tế của repository, nhánh dự án được đặt tên trực tiếp là `ai-agent-video-tutor` thay vì `project/ai-agent-video-tutor`.

## 2. Quy tắc Commit Message

### Cấu trúc commit message

```
<type>: <description>

[optional body]
```

### Các loại commit (Commit Types)

<table>
<tr>
<th>Type</th>
<th>Mô tả</th>
<th>Ví dụ</th>
</tr>
<tr>
<td>feat</td>
<td>Thêm tính năng mới</td>
<td>feat: tích hợp module Docling</td>
</tr>
<tr>
<td>fix</td>
<td>Sửa lỗi</td>
<td>fix: resolve white video issue in pipeline</td>
</tr>
<tr>
<td>docs</td>
<td>Cập nhật tài liệu hoặc README</td>
<td>docs: update installation guide</td>
</tr>
<tr>
<td>refactor</td>
<td>Tối ưu hóa code không thay đổi tính năng</td>
<td>refactor: optimize parser performance</td>
</tr>
<tr>
<td>test</td>
<td>Thêm hoặc sửa test cases</td>
<td>test: add unit tests for AI reviewer</td>
</tr>
<tr>
<td>chore</td>
<td>Cập nhật dependencies, config</td>
<td>chore: update requirements.txt</td>
</tr>
<tr>
<td>style</td>
<td>Format code, không ảnh hưởng logic</td>
<td>style: format Python files with black</td>
</tr>
</table>

### Nguyên tắc viết commit message

1. Không sử dụng emoji trong commit message
2. Viết mô tả ngắn gọn, rõ ràng
3. Sử dụng tiếng Anh hoặc tiếng Việt không dấu
4. Bắt đầu bằng động từ ở dạng nguyên thể
5. Không kết thúc bằng dấu chấm
6. Giới hạn dòng đầu tiên trong 72 ký tự

## 3. Quy trình làm việc thực tế

### Quy trình làm việc với nhánh dev và project

<table>
<tr>
<th>Bước</th>
<th>Hành động</th>
<th>Lệnh</th>
</tr>
<tr>
<td>1</td>
<td>Làm việc trên nhánh dev</td>
<td>git checkout dev/ai-agent-video-tutor/nguyen-van-tong</td>
</tr>
<tr>
<td>2</td>
<td>Commit thay đổi trên nhánh dev</td>
<td>git add . && git commit -m "feat: add new feature"</td>
</tr>
<tr>
<td>3</td>
<td>Push nhánh dev (optional, để backup)</td>
<td>git push mentor dev/ai-agent-video-tutor/nguyen-van-tong</td>
</tr>
<tr>
<td>4</td>
<td>Chuyển về nhánh project chính</td>
<td>git checkout ai-agent-video-tutor</td>
</tr>
<tr>
<td>5</td>
<td>Merge từ dev vào project</td>
<td>git merge dev/ai-agent-video-tutor/nguyen-van-tong</td>
</tr>
<tr>
<td>6</td>
<td>Push nhánh project để mentor review</td>
<td>git push mentor ai-agent-video-tutor</td>
</tr>
</table>

### Bước 1: Kiểm tra nhánh hiện tại

```bash
git branch
git status
```

### Bước 2: Thêm file vào staging area

```bash
# Thêm file cụ thể
git add webreel-ai-agent/src/ai_reviewer.py

# Thêm nhiều file
git add webreel-ai-agent/src/*.py

# Thêm tất cả file đã thay đổi (cẩn thận)
git add .
```

### Bước 3: Commit với message phù hợp

```bash
# Ví dụ thêm tính năng
git commit -m "feat: add AI reviewer module with selector fixing"

# Ví dụ sửa lỗi
git commit -m "fix: resolve white video issue by adding scroll action support"

# Ví dụ cập nhật docs
git commit -m "docs: add Git workflow documentation"

# Ví dụ refactor
git commit -m "refactor: optimize parser to handle extract actions"
```

### Bước 4: Push lên remote

```bash
# Push lên nhánh dự án
git push mentor ai-agent-video-tutor

# Nếu là lần đầu push nhánh mới
git push -u mentor ai-agent-video-tutor
```

## 4. Các tình huống thường gặp

### Quy trình hoàn chỉnh từ dev đến project

```bash
# Bước 1: Đảm bảo đang ở nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong

# Bước 2: Làm việc và commit trên nhánh dev
git add webreel-ai-agent/src/new_feature.py
git commit -m "feat: add new feature for week 1"

# Bước 3: Push nhánh dev lên remote (optional, để backup)
git push mentor dev/ai-agent-video-tutor/nguyen-van-tong

# Bước 4: Chuyển về nhánh project chính
git checkout ai-agent-video-tutor

# Bước 5: Pull để đảm bảo nhánh project là mới nhất
git pull mentor ai-agent-video-tutor

# Bước 6: Merge từ nhánh dev vào nhánh project
git merge dev/ai-agent-video-tutor/nguyen-van-tong

# Bước 7: Giải quyết conflict nếu có, sau đó commit
# (nếu có conflict, sửa file, sau đó git add và git commit)

# Bước 8: Push nhánh project để mentor review
git push mentor ai-agent-video-tutor

# Bước 9: Quay lại nhánh dev để tiếp tục làm việc
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
```

### Commit nhiều file cùng lúc (trên nhánh dev)

```bash
# Đảm bảo đang ở nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong

git add webreel-ai-agent/src/bu_to_webreel.py
git add webreel-ai-agent/src/ai_reviewer.py
git add webreel-ai-agent/README.md
git commit -m "feat: integrate AI reviewer into pipeline"
```

### Sửa commit message vừa tạo (chưa push)

```bash
git commit --amend -m "feat: new correct message"
```

### Xem lịch sử commit

```bash
# Xem lịch sử ngắn gọn
git log --oneline

# Xem lịch sử chi tiết
git log

# Xem thay đổi trong commit
git show <commit-hash>

# Xem lịch sử của cả 2 nhánh
git log --oneline --graph --all
```

### Kiểm tra sự khác biệt giữa nhánh dev và project

```bash
# Xem commit nào ở dev mà chưa có ở project
git log ai-agent-video-tutor..dev/ai-agent-video-tutor/nguyen-van-tong

# Xem file nào khác nhau giữa 2 nhánh
git diff ai-agent-video-tutor..dev/ai-agent-video-tutor/nguyen-van-tong
```

### Kiểm tra file nào sẽ được commit

```bash
git status
git diff
git diff --staged
```

## 5. Checklist trước khi commit

- [ ] Đã kiểm tra nhánh hiện tại (nên là dev branch)
- [ ] Đã test code chạy được (nếu là code change)
- [ ] Đã loại bỏ file test, output, cache không cần thiết
- [ ] Commit message có prefix đúng (feat/fix/docs/refactor)
- [ ] Commit message ngắn gọn, rõ ràng, không có emoji
- [ ] Đã review lại các file sẽ commit bằng `git status`

## 6. Checklist trước khi merge vào nhánh project

- [ ] Đã commit tất cả thay đổi trên nhánh dev
- [ ] Đã test đầy đủ tính năng mới
- [ ] Đã cập nhật tài liệu liên quan (README, docs)
- [ ] Đã pull nhánh project mới nhất trước khi merge
- [ ] Đã kiểm tra không có conflict
- [ ] Đã review lại toàn bộ thay đổi sẽ merge

## 7. Ví dụ commit thực tế từ dự án

### Tuần 1: Setup và tích hợp cơ bản

```bash
# Trên nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
git commit -m "docs: setup project structure and base configuration for week 1"
git commit -m "feat: integrate browser-use with Playwright"
git commit -m "feat: add parser to convert browser-use actions to webreel config"
git commit -m "fix: resolve white video issue by adding scroll action support"

# Merge vào nhánh project
git checkout ai-agent-video-tutor
git merge dev/ai-agent-video-tutor/nguyen-van-tong
git push mentor ai-agent-video-tutor
```

### Tuần 2: AI Reviewer và tối ưu

```bash
# Trên nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
git commit -m "feat: add AI reviewer module with Gemini integration"
git commit -m "feat: integrate AI reviewer into pipeline"
git commit -m "fix: update AI reviewer to prioritize CSS selectors"
git commit -m "refactor: optimize selector fixing logic"

# Merge vào nhánh project
git checkout ai-agent-video-tutor
git merge dev/ai-agent-video-tutor/nguyen-van-tong
git push mentor ai-agent-video-tutor
```

### Tuần 3: TTS và UI

```bash
# Trên nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
git commit -m "feat: integrate FPT.AI TTS for Vietnamese narration"
git commit -m "feat: add Streamlit UI for pipeline control"
git commit -m "docs: update README with TTS setup instructions"

# Merge vào nhánh project
git checkout ai-agent-video-tutor
git merge dev/ai-agent-video-tutor/nguyen-van-tong
git push mentor ai-agent-video-tutor
```

### Tuần 4: Video composition

```bash
# Trên nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
git commit -m "feat: add MoviePy integration for audio-video sync"
git commit -m "feat: implement Bezier curve animation for cursor"
git commit -m "fix: resolve audio sync timing issues"

# Merge vào nhánh project
git checkout ai-agent-video-tutor
git merge dev/ai-agent-video-tutor/nguyen-van-tong
git push mentor ai-agent-video-tutor
```

### Tuần 5: Docker và finalization

```bash
# Trên nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
git commit -m "feat: add Docker configuration with layer caching"
git commit -m "docs: add deployment guide"
git commit -m "feat: generate 5 demo videos"

# Merge vào nhánh project
git checkout ai-agent-video-tutor
git merge dev/ai-agent-video-tutor/nguyen-van-tong
git push mentor ai-agent-video-tutor
```

## 8. Remote repository

### Thông tin remote

```bash
# Xem danh sách remote
git remote -v

# Kết quả mong đợi
mentor  git@github.com:AI-RDI/pre-ai-edtech.git (fetch)
mentor  git@github.com:AI-RDI/pre-ai-edtech.git (push)
```

### Thêm remote (nếu chưa có)

```bash
git remote add mentor git@github.com:AI-RDI/pre-ai-edtech.git
```

## 9. Lưu ý quan trọng

1. Không commit file nhạy cảm (.env, API keys)
2. Không commit file test, output, cache
3. Luôn làm việc trên nhánh dev, chỉ merge vào project khi hoàn thành
4. Luôn pull nhánh project trước khi merge để tránh conflict
5. Commit thường xuyên với message rõ ràng trên nhánh dev
6. Mỗi commit nên tập trung vào một thay đổi cụ thể
7. Không dùng `git add .` mà không kiểm tra kỹ
8. Tuân thủ .gitignore để tránh commit file không cần thiết
9. Nhánh dev là nơi thử nghiệm, nhánh project là nơi code ổn định
10. Mentor sẽ review code từ nhánh project, không phải nhánh dev

## 10. Quy trình báo cáo hàng tuần

### Cập nhật ISSUES_REPORT.md

File `webreel-ai-agent/ISSUES_REPORT.md` ghi lại tiến độ, vấn đề và giải pháp của từng tuần.

<table>
<tr>
<th>Thời điểm</th>
<th>Hành động</th>
<th>Nhánh</th>
</tr>
<tr>
<td>Thứ 6 hàng tuần</td>
<td>Cập nhật ISSUES_REPORT.md với tiến độ tuần hiện tại</td>
<td>ai-agent-video-tutor (nhánh gốc)</td>
</tr>
<tr>
<td>Cuối tuần</td>
<td>Merge code từ nhánh dev vào nhánh project</td>
<td>dev → ai-agent-video-tutor</td>
</tr>
</table>

### Quy trình cập nhật báo cáo

```bash
# Bước 1: Chuyển về nhánh project chính
git checkout ai-agent-video-tutor

# Bước 2: Pull để đảm bảo nhánh mới nhất
git pull mentor ai-agent-video-tutor

# Bước 3: Cập nhật ISSUES_REPORT.md
# Mở file và thêm nội dung tuần mới

# Bước 4: Commit báo cáo
git add webreel-ai-agent/ISSUES_REPORT.md
git commit -m "docs: update weekly report for week X"

# Bước 5: Push lên remote
git push mentor ai-agent-video-tutor
```

### Cấu trúc báo cáo tuần

Mỗi tuần thêm section mới vào ISSUES_REPORT.md:

```markdown
# Báo Cáo Tuần X: [Tên nhiệm vụ chính]

## Mục Tiêu Tuần X
[Mô tả mục tiêu theo kế hoạch]

## Những Gì Đã Làm Được
1. [Tính năng/module đã hoàn thành]
2. [Test cases đã pass]
3. [Tài liệu đã viết]

## Các Vấn Đề Gặp Phải
1. [Vấn đề 1 và cách giải quyết]
2. [Vấn đề 2 và cách giải quyết]

## Kết Quả Đạt Được
[Tổng kết ngắn gọn]

## Bài Học Rút Ra
[Những điều học được trong tuần]
```

### Quy trình merge code cuối tuần

```bash
# Bước 1: Đảm bảo code trên nhánh dev đã commit hết
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
git status  # Kiểm tra không còn file chưa commit

# Bước 2: Chuyển về nhánh project
git checkout ai-agent-video-tutor

# Bước 3: Pull nhánh project mới nhất
git pull mentor ai-agent-video-tutor

# Bước 4: Merge code từ dev
git merge dev/ai-agent-video-tutor/nguyen-van-tong

# Bước 5: Giải quyết conflict nếu có

# Bước 6: Push lên remote
git push mentor ai-agent-video-tutor

# Bước 7: Quay lại nhánh dev để tiếp tục làm việc tuần sau
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
```

### Lưu ý quan trọng

1. Báo cáo ISSUES_REPORT.md luôn được cập nhật trên nhánh project (ai-agent-video-tutor)
2. Code development làm trên nhánh dev, cuối tuần merge vào project
3. Báo cáo nên được cập nhật trước khi merge code
4. Mỗi tuần có một section riêng trong ISSUES_REPORT.md
5. Báo cáo phải ngắn gọn, tập trung vào kết quả và vấn đề chính

## 11. Tham khảo thêm

- Conventional Commits: https://www.conventionalcommits.org/
- Git Best Practices: https://git-scm.com/book/en/v2
- Repository mentor: https://github.com/AI-RDI/pre-ai-edtech
