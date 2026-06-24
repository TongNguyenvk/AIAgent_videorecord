# Danh Sách File Cần Commit

Tài liệu này liệt kê tất cả các file cần commit theo yêu cầu, tuân thủ quy tắc trong `docs/GIT_WORKFLOW.md`.

## Thông Tin Commit

- Nhánh hiện tại: `dev/ai-agent-video-tutor/nguyen-van-tong`
- Nhánh đích: `ai-agent-video-tutor` (sau khi merge)
- Remote: `mentor`

## 1. File Python trong thư mục os_recorder

### File đã sửa đổi (Modified)
```
M webreel-ai-agent/os_recorder/core/os_executor_v2.py
M webreel-ai-agent/os_recorder/core/os_planning_agent.py
M webreel-ai-agent/os_recorder/core/os_planning_agent_v2.py
M webreel-ai-agent/os_recorder/core/sync_recorder.py
```

### File mới tạo (New/Untracked)
```
?? webreel-ai-agent/os_recorder/core/powerpoint_adapter.py
?? webreel-ai-agent/os_recorder/os_pipeline_dual_output.py
?? webreel-ai-agent/os_recorder/os_pipeline_main.py
?? webreel-ai-agent/os_recorder/os_pipeline_v2_old.py
?? webreel-ai-agent/os_recorder/os_pipeline_v3_dual_flat_structure.py
```

### File đã xóa (Deleted)
```
D webreel-ai-agent/os_recorder/os_pipeline_v2.py
```

## 2. File Python trong thư mục dual_output_pipeline

### File đã sửa đổi (Modified)
```
M webreel-ai-agent/dual_output_pipeline/core/screenshot_capture.py
M webreel-ai-agent/dual_output_pipeline/renderers/document_renderer.py
M webreel-ai-agent/dual_output_pipeline/renderers/pdf_renderer.py
```

## 3. File Python trong thư mục desktop_app

### File đã sửa đổi (Modified)
```
M webreel-ai-agent/desktop_app/__init__.py
```

### Lưu ý
- Không commit các file trong folder v3/ theo yêu cầu

## 4. File Python ở root

### File đã sửa đổi (Modified)
```
M webreel-ai-agent/app_flet_unified.py
```

## 5. File requirements.txt

### File đã sửa đổi (Modified)
```
M webreel-ai-agent/requirements.txt
M webreel-ai-agent/os_recorder/requirements.txt
M webreel-ai-agent/desktop_app/requirements.txt
```

## Tổng Kết

### Tổng số file cần commit: 17 files

- File đã sửa đổi (Modified): 11 files
- File mới tạo (New): 5 files
- File đã xóa (Deleted): 1 file

### Phân loại theo thư mục:

1. **os_recorder/**: 9 files (4 modified, 5 new)
2. **dual_output_pipeline/**: 3 files (3 modified)
3. **desktop_app/**: 1 file (1 modified, không bao gồm v3/)
4. **root (app_flet_unified.py)**: 1 file (1 modified)
5. **requirements.txt**: 3 files (3 modified)

## Quy Trình Commit Đề Xuất

### Bước 1: Kiểm tra nhánh hiện tại
```bash
git branch
git status
```

### Bước 2: Commit theo nhóm chức năng

#### Commit 1: OS Recorder Core Improvements
```bash
git add webreel-ai-agent/os_recorder/core/os_executor_v2.py
git add webreel-ai-agent/os_recorder/core/os_planning_agent.py
git add webreel-ai-agent/os_recorder/core/os_planning_agent_v2.py
git add webreel-ai-agent/os_recorder/core/sync_recorder.py
git add webreel-ai-agent/os_recorder/core/powerpoint_adapter.py
git commit -m "feat: improve OS recorder core with loop detection and PowerPoint support"
```

#### Commit 2: OS Recorder Pipeline Updates
```bash
git add webreel-ai-agent/os_recorder/os_pipeline_dual_output.py
git add webreel-ai-agent/os_recorder/os_pipeline_main.py
git add webreel-ai-agent/os_recorder/os_pipeline_v2_old.py
git add webreel-ai-agent/os_recorder/os_pipeline_v3_dual_flat_structure.py
git rm webreel-ai-agent/os_recorder/os_pipeline_v2.py
git commit -m "refactor: restructure OS recorder pipelines with dual output support"
```

#### Commit 3: Dual Output Pipeline Improvements
```bash
git add webreel-ai-agent/dual_output_pipeline/core/screenshot_capture.py
git add webreel-ai-agent/dual_output_pipeline/renderers/document_renderer.py
git add webreel-ai-agent/dual_output_pipeline/renderers/pdf_renderer.py
git commit -m "feat: enhance dual output pipeline with improved screenshot and rendering"
```

#### Commit 4: Desktop App Update
```bash
git add webreel-ai-agent/desktop_app/__init__.py
git commit -m "feat: update desktop app initialization"
```

#### Commit 5: Unified Flet App Update
```bash
git add webreel-ai-agent/app_flet_unified.py
git commit -m "feat: update unified Flet app with session management and UI improvements"
```

#### Commit 6: Dependencies Update
```bash
git add webreel-ai-agent/requirements.txt
git add webreel-ai-agent/os_recorder/requirements.txt
git add webreel-ai-agent/desktop_app/requirements.txt
git commit -m "chore: update dependencies for all modules"
```

### Bước 3: Push lên nhánh dev (optional, để backup)
```bash
git push mentor dev/ai-agent-video-tutor/nguyen-van-tong
```

### Bước 4: Merge vào nhánh project
```bash
# Chuyển về nhánh project
git checkout ai-agent-video-tutor

# Pull để đảm bảo nhánh project là mới nhất
git pull mentor ai-agent-video-tutor

# Merge từ nhánh dev
git merge dev/ai-agent-video-tutor/nguyen-van-tong

# Push để mentor review
git push mentor ai-agent-video-tutor

# Quay lại nhánh dev
git checkout dev/ai-agent-video-tutor/nguyen-van-tong
```

## Lưu Ý Quan Trọng

1. Không commit emoji trong message
2. Sử dụng prefix phù hợp: feat, fix, refactor, chore
3. Message ngắn gọn, rõ ràng, dưới 72 ký tự
4. Kiểm tra kỹ file trước khi commit bằng `git status`
5. Test code trước khi commit
6. Loại bỏ file test, output, cache không cần thiết
7. Luôn làm việc trên nhánh dev, chỉ merge vào project khi hoàn thành

## Checklist Trước Khi Commit

- [ ] Đã kiểm tra nhánh hiện tại (dev branch)
- [ ] Đã test code chạy được
- [ ] Đã loại bỏ file không cần thiết
- [ ] Commit message có prefix đúng
- [ ] Commit message ngắn gọn, rõ ràng
- [ ] Đã review lại các file bằng `git status`
- [ ] Đã cập nhật tài liệu liên quan nếu cần

## Checklist Trước Khi Merge

- [ ] Đã commit tất cả thay đổi trên nhánh dev
- [ ] Đã test đầy đủ tính năng mới
- [ ] Đã cập nhật tài liệu (README, docs)
- [ ] Đã pull nhánh project mới nhất
- [ ] Đã kiểm tra không có conflict
- [ ] Đã review lại toàn bộ thay đổi
