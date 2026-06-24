# Kế Hoạch Test OS Recorder - Thứ 6

## Mục Tiêu Chính

Kiểm tra và cải thiện khả năng của OS Recorder trong việc tự động hóa Excel (đã có excel_engine.py), sau đó thử nghiệm với các ứng dụng đơn giản khác như Notepad, Paint trước khi tiến tới Office phức tạp hơn.

## Tổng Quan Kiến Trúc OS Recorder

### Các Module Chính

<table>
<tr>
<th>Module</th>
<th>Chức năng</th>
<th>Trạng thái</th>
</tr>
<tr>
<td>os_pipeline.py</td>
<td>Pipeline chính điều phối toàn bộ quy trình</td>
<td>Đã có</td>
</tr>
<tr>
<td>window_manager.py</td>
<td>Quản lý cửa sổ ứng dụng (focus, resize, position)</td>
<td>Đã có</td>
</tr>
<tr>
<td>ui_inspector.py</td>
<td>Phân tích UI elements bằng UI Automation</td>
<td>Đã có</td>
</tr>
<tr>
<td>vision_agent.py</td>
<td>AI vision để nhận diện UI qua screenshot</td>
<td>Đã có</td>
</tr>
<tr>
<td>os_planning_agent.py</td>
<td>AI agent lập kế hoạch các bước thực hiện</td>
<td>Đã có</td>
</tr>
<tr>
<td>os_executor.py</td>
<td>Thực thi các action (click, type, scroll)</td>
<td>Đã có</td>
</tr>
<tr>
<td>excel_engine.py</td>
<td>Tương tác trực tiếp với Excel qua COM</td>
<td>Đã có</td>
</tr>
<tr>
<td>sync_recorder.py</td>
<td>Ghi lại video đồng bộ với actions</td>
<td>Đã có</td>
</tr>
<tr>
<td>media_engine.py</td>
<td>Xử lý video, audio, composition</td>
<td>Đã có</td>
</tr>
</table>

### Quy Trình Hoạt Động

```
User Prompt
    ↓
Planning Agent (Gemini)
    ↓
Action Plan (JSON)
    ↓
OS Executor + Sync Recorder
    ↓
Raw Video + Trace
    ↓
TTS Generation
    ↓
Media Composition
    ↓
Final Video
```

## Kế Hoạch Test Thứ 6

### Phần 1: Test Excel với COM API (Buổi Sáng 8h-10h)

Excel đã có `excel_engine.py` sử dụng COM API trực tiếp, nên có độ tin cậy cao hơn.

#### Test Case 1: Excel Cơ Bản (Đã có test)
```python
# test_excel_coordinates.py đã có
# Kiểm tra lại và cải thiện

Expected Actions:
1. Open Excel via COM
2. Create new workbook
3. Write data to cells
4. Format cells (color, bold)
5. Save file
```

#### Test Case 2: Excel với Formula
```python
# Tạo test mới
Scenario: "Tao bang tinh tong doanh thu"

Expected Actions:
1. Open Excel
2. Write headers (Thang, Doanh Thu, Tong)
3. Write sample data
4. Add SUM formula
5. Format as currency
6. Save file
```

#### Test Case 3: Excel với Chart
```python
# Test nâng cao
Scenario: "Tao bieu do cot tu du lieu"

Expected Actions:
1. Open Excel with data
2. Select data range
3. Insert column chart
4. Format chart title
5. Save file
```

### Phần 2: Test Notepad (Buổi Sáng 10h-11h)

Notepad đơn giản, dùng để test UI Automation và Vision Agent.

#### Test Case 4: Notepad Cơ Bản
```
Scenario: "Mo Notepad va viet Hello World"

Expected Actions:
1. Launch notepad.exe
2. Focus window
3. Type "Hello World"
4. Save as test.txt
```

#### Test Case 5: Notepad với Menu
```
Scenario: "Mo Notepad, viet text, format font"

Expected Actions:
1. Launch Notepad
2. Type text
3. Open Format menu
4. Change font
5. Save file
```

### Phần 3: Test Paint (Buổi Sáng 11h-12h)

Paint để test mouse actions (click, drag).

#### Test Case 6: Paint Vẽ Đơn Giản
```
Scenario: "Mo Paint va ve hinh chu nhat"

Expected Actions:
1. Launch mspaint.exe
2. Select rectangle tool
3. Draw rectangle
4. Fill with color
5. Save as image
```

### Phần 3: Phân Tích Kết Quả (Buổi Chiều 13h-14h)

#### Metrics Đánh Giá

<table>
<tr>
<th>Tiêu chí</th>
<th>Cách đo</th>
<th>Mục tiêu</th>
</tr>
<tr>
<td>Excel COM Success</td>
<td>Số test case Excel pass / tổng số</td>
<td>≥ 90% (vì dùng COM)</td>
</tr>
<tr>
<td>UI Automation Success</td>
<td>Notepad, Paint test pass</td>
<td>≥ 60% (đang thử nghiệm)</td>
</tr>
<tr>
<td>Element Detection</td>
<td>Số element tìm được / tổng số cần</td>
<td>≥ 70%</td>
</tr>
<tr>
<td>Video Quality</td>
<td>Độ mượt, đồng bộ audio</td>
<td>30 FPS, sync ±100ms</td>
</tr>
<tr>
<td>Execution Time</td>
<td>Thời gian hoàn thành task</td>
<td>< 2x thời gian thực</td>
</tr>
</table>

#### Vấn Đề Cần Theo Dõi

1. Excel COM API
   - Workbook busy state
   - Cell coordinate accuracy
   - Chart creation stability
   - Save timing

2. UI Automation với Simple Apps
   - Notepad menu detection
   - Paint tool selection
   - Dialog handling (Save As)
   - Keyboard shortcuts

3. Vision Agent Performance
   - Button recognition
   - Menu item detection
   - Icon identification
   - Text OCR accuracy

4. Recording Quality
   - Frame rate stability
   - Mouse cursor visibility
   - Action timing
   - Audio sync

### Phần 4: Setup Sandbox và Cải Thiện (Buổi Chiều 14h-17h)

#### Priority Tasks

1. High Priority (14h-15h)
   - Fix Excel busy state issue (đã có test_excel_busy_fix.py)
   - Improve coordinate detection
   - Add retry logic for COM operations

2. Medium Priority (15h-16h)
   - Setup sandbox structure
   - Create test scenarios for simple apps
   - Improve UI element detection

3. Low Priority (16h-17h)
   - Add logging
   - Document findings
   - Plan next week tasks

## Kế Hoạch Sandbox cho OS Recorder

### Mục Đích Sandbox

Tạo môi trường test an toàn, độc lập để:
- Test các tính năng mới không ảnh hưởng code chính
- Thử nghiệm với các Office apps khác nhau
- Debug và phân tích lỗi dễ dàng
- Rollback nhanh khi có vấn đề

### Cấu Trúc Sandbox

```
webreel-ai-agent/
├── os_recorder/              # Production code
│   ├── core/
│   │   ├── excel_engine.py   # Đã có, hoạt động tốt
│   │   ├── window_manager.py
│   │   ├── ui_inspector.py
│   │   └── ...
│   ├── os_pipeline.py
│   └── requirements.txt
│
└── os_recorder_sandbox/      # Sandbox environment
    ├── test_apps/            # Test với apps đơn giản
    │   ├── test_excel_basic.py
    │   ├── test_excel_formula.py
    │   ├── test_notepad.py
    │   └── test_paint.py
    │
    ├── test_scenarios/       # Kịch bản test JSON
    │   ├── excel_basic.json
    │   ├── excel_chart.json
    │   ├── notepad_simple.json
    │   └── paint_draw.json
    │
    ├── test_data/           # Dữ liệu test
    │   ├── sample.xlsx
    │   ├── sample.txt
    │   └── images/
    │
    ├── output/              # Kết quả test
    │   ├── videos/
    │   ├── traces/
    │   └── logs/
    │
    ├── sandbox_runner.py    # Runner cho sandbox
    └── README.md           # Hướng dẫn sử dụng
```

### Tính Năng Sandbox

#### 1. Isolated Environment

```python
# sandbox_runner.py
class SandboxRunner:
    def __init__(self):
        self.workspace = "os_recorder_sandbox/test_data"
        self.output = "os_recorder_sandbox/output"
        self.use_temp_files = True
        self.auto_cleanup = True
    
    def run_test(self, scenario_file):
        # Load scenario
        # Setup isolated workspace
        # Run test
        # Collect results
        # Cleanup if needed
        pass
```

#### 2. Scenario-Based Testing

```json
// test_scenarios/excel_basic.json
{
  "name": "Excel Basic Test",
  "app": "excel",
  "method": "com_api",
  "steps": [
    {
      "action": "open_excel",
      "params": {}
    },
    {
      "action": "create_workbook",
      "params": {}
    },
    {
      "action": "write_cell",
      "params": {"cell": "A1", "value": "Hello"}
    },
    {
      "action": "write_cell",
      "params": {"cell": "B1", "value": "World"}
    },
    {
      "action": "save_as",
      "params": {"filename": "test_output.xlsx"}
    }
  ],
  "expected_output": {
    "file_exists": true,
    "cell_A1": "Hello",
    "cell_B1": "World"
  }
}
```

```json
// test_scenarios/notepad_simple.json
{
  "name": "Notepad Simple Test",
  "app": "notepad",
  "method": "ui_automation",
  "steps": [
    {
      "action": "launch_app",
      "params": {"exe": "notepad.exe"}
    },
    {
      "action": "type_text",
      "params": {"text": "Hello World"}
    },
    {
      "action": "save_as",
      "params": {"filename": "test.txt"}
    }
  ],
  "expected_output": {
    "file_exists": true,
    "file_content": "Hello World"
  }
}
```

#### 3. Comparison Testing

```python
# So sánh kết quả giữa các phiên bản
class ComparisonTester:
    def compare_versions(self, scenario, version_a, version_b):
        result_a = self.run_with_version(scenario, version_a)
        result_b = self.run_with_version(scenario, version_b)
        
        return {
            "success_rate_diff": result_b.success - result_a.success,
            "performance_diff": result_b.time - result_a.time,
            "quality_diff": result_b.quality - result_a.quality
        }
```

#### 4. Mock và Stub

```python
# Mock Excel COM cho test nhanh
class MockExcelCOM:
    def __init__(self):
        self.workbooks = []
        self.active_workbook = None
    
    def create_workbook(self):
        wb = MockWorkbook()
        self.workbooks.append(wb)
        self.active_workbook = wb
        return wb
    
    def save(self, filename):
        # Simulate save
        time.sleep(0.1)
        return True

# Mock Notepad cho test UI Automation
class MockNotepad:
    def __init__(self):
        self.text = ""
        self.window_handle = None
    
    def type_text(self, text):
        self.text += text
    
    def save_as(self, filename):
        with open(filename, 'w') as f:
            f.write(self.text)
```

### Quy Trình Sử Dụng Sandbox

#### Bước 1: Setup Sandbox

```bash
# Tạo môi trường sandbox
cd webreel-ai-agent
mkdir -p os_recorder_sandbox/{experiments,test_scenarios,test_data,output}

# Copy sample data
cp sample_files/*.pptx os_recorder_sandbox/test_data/
cp sample_files/*.docx os_recorder_sandbox/test_data/
```

#### Bước 2: Tạo Test Scenario

```bash
# Tạo scenario cho Excel
python os_recorder_sandbox/create_scenario.py \
  --name "Excel Formula Test" \
  --app excel \
  --method com_api \
  --steps steps.json

# Tạo scenario cho Notepad
python os_recorder_sandbox/create_scenario.py \
  --name "Notepad Simple" \
  --app notepad \
  --method ui_automation \
  --steps steps.json
```

#### Bước 3: Run Test

```bash
# Test Excel với COM API
python os_recorder_sandbox/sandbox_runner.py \
  --scenario test_scenarios/excel_basic.json \
  --output output/excel_test_001

# Test Notepad với UI Automation
python os_recorder_sandbox/sandbox_runner.py \
  --scenario test_scenarios/notepad_simple.json \
  --output output/notepad_test_001
```

#### Bước 4: Analyze Results

```bash
# Phân tích kết quả
python os_recorder_sandbox/analyze_results.py \
  --test-run output/test_001 \
  --compare-with output/test_000
```

#### Bước 5: Promote to Production

```bash
# Nếu test pass, merge vào production
python os_recorder_sandbox/promote.py \
  --experiment experiments/powerpoint_engine.py \
  --target os_recorder/core/powerpoint_engine.py
```

### Safety Features

#### 1. Auto Backup

```python
# Tự động backup trước khi test
class SafetyManager:
    def backup_before_test(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/backup_{timestamp}"
        shutil.copytree("os_recorder", backup_dir)
```

#### 2. Rollback Mechanism

```python
# Rollback nếu test fail
def rollback_on_failure(backup_dir):
    if test_failed:
        shutil.rmtree("os_recorder")
        shutil.copytree(backup_dir, "os_recorder")
```

#### 3. Resource Limits

```python
# Giới hạn tài nguyên cho sandbox
class ResourceLimiter:
    MAX_EXECUTION_TIME = 300  # 5 minutes
    MAX_MEMORY_MB = 2048
    MAX_FILE_SIZE_MB = 100
    
    def enforce_limits(self, process):
        # Monitor and kill if exceeded
        pass
```

## Timeline Thứ 6

<table>
<tr>
<th>Thời gian</th>
<th>Hoạt động</th>
<th>Output</th>
</tr>
<tr>
<td>08:00 - 08:30</td>
<td>Setup môi trường test, chuẩn bị sample files</td>
<td>Test environment ready</td>
</tr>
<tr>
<td>08:30 - 10:00</td>
<td>Test PowerPoint (3 test cases)</td>
<td>Test results, videos, logs</td>
</tr>
<tr>
<td>10:00 - 10:15</td>
<td>Break, review kết quả PowerPoint</td>
<td>Notes về issues</td>
</tr>
<tr>
<td>10:15 - 12:00</td>
<td>Test Word (3 test cases)</td>
<td>Test results, videos, logs</td>
</tr>
<tr>
<td>12:00 - 13:00</td>
<td>Lunch break</td>
<td>-</td>
</tr>
<tr>
<td>13:00 - 14:00</td>
<td>Phân tích kết quả, tính metrics</td>
<td>Test report với metrics</td>
</tr>
<tr>
<td>14:00 - 15:00</td>
<td>Setup sandbox environment</td>
<td>Sandbox structure ready</td>
</tr>
<tr>
<td>15:00 - 16:30</td>
<td>Fix critical bugs, implement improvements</td>
<td>Bug fixes, code updates</td>
</tr>
<tr>
<td>16:30 - 17:00</td>
<td>Re-test failed cases, document findings</td>
<td>Final report, next steps</td>
</tr>
</table>

## Deliverables Cuối Ngày

1. Test Report
   - Kết quả 6 test cases
   - Metrics và phân tích
   - Screenshots và videos
   - Issues list với priority

2. Sandbox Environment
   - Cấu trúc folder hoàn chỉnh
   - Sample scenarios
   - Documentation

3. Code Updates
   - Bug fixes
   - Improvements
   - New features (nếu có)

4. Documentation
   - Test findings
   - Known issues
   - Workarounds
   - Next steps

## Rủi Ro và Mitigation

<table>
<tr>
<th>Rủi ro</th>
<th>Impact</th>
<th>Mitigation</th>
</tr>
<tr>
<td>Office apps không stable</td>
<td>High</td>
<td>Có backup plan với mock objects</td>
</tr>
<tr>
<td>UI Automation không hoạt động</td>
<td>High</td>
<td>Fallback sang Vision Agent</td>
</tr>
<tr>
<td>Test mất nhiều thời gian</td>
<td>Medium</td>
<td>Ưu tiên test cases quan trọng</td>
</tr>
<tr>
<td>Bugs phức tạp khó fix</td>
<td>Medium</td>
<td>Document và defer sang tuần sau</td>
</tr>
<tr>
<td>Sandbox setup phức tạp</td>
<td>Low</td>
<td>Bắt đầu với cấu trúc đơn giản</td>
</tr>
</table>

## Success Criteria

Test ngày thứ 6 được coi là thành công nếu:

1. Ít nhất 4/6 test cases pass (≥ 67%)
2. Có video demo cho ít nhất 2 test cases
3. Sandbox environment được setup xong
4. Document đầy đủ findings và issues
5. Có kế hoạch rõ ràng cho tuần sau

## Next Steps (Tuần Sau)

1. Implement PowerPoint Engine và Word Engine riêng biệt
2. Improve Vision Agent cho Office UI
3. Add more test scenarios
4. Optimize performance
5. Integrate với desktop app UI
