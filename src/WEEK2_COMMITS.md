# Kế hoạch Commit Mẫu (Tuần 2: Parser, AI Reviewer & Core Fixes)

Dựa trên tiến độ công việc Tuần 2, dưới đây là chi tiết lịch trình mô phỏng các lượt commit cho 5 ngày làm việc. Kế hoạch này đã được tinh chỉnh để bao gồm cả các bản vá quan trọng ở mức Core của Webreel (sửa lỗi gõ phím, fix timeline khung hình) và **bỏ qua các file rác sinh ra trong quá trình build/test**.

*(Lưu ý: Trước khi commit, hãy đảm bảo file `.gitignore` đã chặn các thư mục như `output/`, `.webreel/`, `venv/`, `node_modules/`, và các file `*.map`, `*.d.ts`, `*.js` sinh ra từ tsconfig trong `packages/`.)*

## Ngày 1: Khởi tạo Parser cơ bản & Fix Core Keyboard Event
*   **Mục tiêu:** Parse được history từ browser-use. Đồng thời sửa lỗi Dispatch Event "Enter" trên CDP Chrome để các webapp React nhận được phím Enter khi submit form.
*   **Các file ảnh hưởng chính:** 
    *   `webreel-ai-agent/src/bu_to_webreel.py`
    *   `packages/@webreel/core/src/actions.ts`
*   **Lệnh Commit:**
    ```bash
    git add webreel-ai-agent/src/bu_to_webreel.py packages/@webreel/core/src/actions.ts
    git commit -m "feat(core/parser): fix CDP Enter keystroke & init parser basic extraction"
    ```

## Ngày 2: Đồng bộ thuyết minh & Độ ổn định TTS (Audio Sync & Stability)
*   **Mục tiêu:** Khắc phục triệt để lỗi lệch lời thoại ("one step ahead") bằng cách tách thuyết minh thành các bước pause độc lập. Triển khai cơ chế retry cho TTS để xử lý lỗi mạng/FPT.AI. Tối ưu bộ lọc ffmpeg để đảm bảo âm lượng to, rõ.
*   **Các file ảnh hưởng chính:** 
    *   `webreel-ai-agent/src/bu_to_webreel.py` (standalone pause steps)
    *   `webreel-ai-agent/src/tts.py` (retry mechanism & polling)
    *   `webreel-ai-agent/src/trace_composer.py` (adelay & volume normalization)
    *   `docs/Problem-Solving Path.md` (documentation of issues & fixes)
*   **Lệnh Commit:**
    ```bash
    git add webreel-ai-agent/src/bu_to_webreel.py webreel-ai-agent/src/tts.py webreel-ai-agent/src/trace_composer.py docs/Problem-Solving\ Path.md
    git commit -m "fix(sync): resolve narration alignment drift & implement robust TTS retries"
    ```

## Ngày 3: Tích hợp AI Reviewer bằng Gemini & Chỉnh thông số Unified Pipeline
*   **Mục tiêu:** Tích hợp Gemini API review file Webreel config theo chuẩn Schema V1. Đồng thời tinh chỉnh các thông số delay (chuột, phím) của `run_pipeline_unified_chrome.py` cho ăn khớp với Webreel engine.
*   **Các file ảnh hưởng chính:** 
    *   `webreel-ai-agent/src/ai_reviewer.py`
    *   `webreel-ai-agent/run_pipeline_unified_chrome.py`
*   **Lệnh Commit:**
    ```bash
    git add webreel-ai-agent/src/ai_reviewer.py webreel-ai-agent/run_pipeline_unified_chrome.py
    git commit -m "feat(ai-reviewer): integrate Gemini layout analysis and tune unified pipeline timings"
    ```

## Ngày 4: Sinh Kịch bản TTS & Đồng bộ Cực biên (Audio Sync)
*   **Mục tiêu:** Sinh kịch bản lồng tiếng tiếng Việt hoàn chỉnh. Cân đo tính tiêm thời lượng `pause`. Offset `start_time` -1.5s để audio vang lên dự báo trước hành động UI, thiết kế injection CDP URL mượt mà.
*   **Các file ảnh hưởng chính:** 
    *   `webreel-ai-agent/src/ai_reviewer.py`
    *   `webreel-ai-agent/run_pipeline_unified_chrome.py`
*   **Lệnh Commit:**
    ```bash
    git add webreel-ai-agent/src/ai_reviewer.py webreel-ai-agent/run_pipeline_unified_chrome.py
    git commit -m "feat(ai-reviewer): inject TTS pause syncs and premeditation timing limits"
    ```

## Ngày 5: Kiểm thử hoàn chỉnh (Testing) & Viết tài liệu (Documentation)
*   **Mục tiêu:** Viết file mô tả các kiến trúc Parser (`BU_TO_WEBREEL.md`) và AI (`AI_REVIEWER.md`). Cập nhật `README.md` tuần 2 tổng quan. Update các file HTML test case.
*   **Các file ảnh hưởng chính:** 
    *   `docs/BU_TO_WEBREEL.md`
    *   `docs/AI_REVIEWER.md`
    *   `webreel-ai-agent/test-cases/*`
    *   `README.md`
*   **Lệnh Commit:**
    ```bash
    git add docs/ webreel-ai-agent/test-cases/ README.md
    git commit -m "docs: generate documentation for parser & AI modules with HTML test environments"
    ```
