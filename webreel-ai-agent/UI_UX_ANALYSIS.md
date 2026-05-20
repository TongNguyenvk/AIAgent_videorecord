# UI/UX Analysis & Job Routing System Design

## 1. Tổng quan hệ thống hiện tại

### 1.1 Kiến trúc Worker

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Worker    │    │Presentation Wkr │    │   OS Worker     │
│  (web-queue)    │    │(presentation-q) │    │  (os-queue)     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│• GitHub tutorial│    │• PowerPoint     │    │• Desktop apps   │
│• Website demo   │    │• OneDrive auth  │    │• Native UI      │
│• Browser auto   │    │• Slide narration│    │• Windows only   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 1.2 Pipeline V3 Flow

```
Phase 1: Scout (browser-use) → Narrations
Phase 2: Parser → Webreel config + TTS script
Phase 3: TTS → Audio files (Edge/FPT)
Phase 4: Injector → Exact timing
Phase 5: Execution → Video recording
Phase 6: Composer → Final video with audio
```

## 2. UI/UX Requirements Analysis

### 2.1 User Journey Mapping

#### 2.1.1 Web Tutorial Creator

```
User Intent: "Tạo video hướng dẫn sử dụng website"
Steps:
1. Nhập task description (VD: "Hướng dẫn đăng ký GitHub")
2. Chọn settings (voice, engine, padding)
3. Submit → Web Worker
4. Monitor progress (Phase 1-6)
5. Download video
```

#### 2.1.2 Presentation Creator

```
User Intent: "Tạo video thuyết trình từ PowerPoint"
Steps:
1. Upload PPTX file
2. Nhập mô tả ngắn (optional)
3. Chọn TTS settings
4. Submit → Presentation Worker
5. Monitor progress
6. Download video
```

#### 2.1.3 Desktop App Demo Creator

```
User Intent: "Quay video demo ứng dụng desktop"
Steps:
1. Nhập task description
2. Chọn target OS/app
3. Submit → OS Worker (Windows)
4. Monitor progress
5. Download video
```

### 2.2 Core UI Components Needed

#### 2.2.1 Job Creation Interface

```
┌─────────────────────────────────────────────────────────────┐
│                    Create New Video                         │
├─────────────────────────────────────────────────────────────┤
│ Job Type: [Web Tutorial ▼] [Presentation ▼] [Desktop App ▼]│
│                                                             │
│ Task Description:                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Describe what you want to demonstrate...                │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ File Upload (for Presentation):                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [📁 Choose PPTX File] or drag & drop                   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Settings:                                                   │
│ • Voice: [banmai ▼] [leminh ▼] [myan ▼]                   │
│ • Engine: [Edge TTS ▼] [FPT.AI ▼]                         │
│ • Padding: [300ms ▼]                                       │
│                                                             │
│                           [Create Video] [Cancel]          │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.2 Job Monitoring Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                    Job Dashboard                            │
├─────────────────────────────────────────────────────────────┤
│ Active Jobs (3)                          [Refresh] [Auto ✓]│
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🎬 GitHub Tutorial                    [Phase 3: TTS]   │ │
│ │ ID: 88cc03eb... | Web Worker | 2 min ago              │ │
│ │ ████████████████░░░░ 80%                               │ │
│ │                                    [View] [Cancel]     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📊 Sales Presentation                [Phase 1: Scout]  │ │
│ │ ID: 2440f16c... | Presentation Worker | 30s ago       │ │
│ │ ████░░░░░░░░░░░░░░░░ 20%                               │ │
│ │                                    [View] [Cancel]     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Completed Jobs (12)                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ✅ Excel Tutorial                     [Completed]      │ │
│ │ ID: a7c1475f... | Web Worker | 1 hour ago             │ │
│ │ 📹 test_web_tutorial_v3_final.mp4 (10.2MB)           │ │
│ │                          [Download] [View] [Delete]    │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.3 Phase 2.5 Review Interface (Critical UX)

```
┌─────────────────────────────────────────────────────────────┐
│              TTS Script Review - Job 88cc03eb               │
├─────────────────────────────────────────────────────────────┤
│ ⚠️  Review narration before generating audio (Phase 2.5)    │
│                                                             │
│ Segment 1/5:                                    [🔊 Play]  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Chào mừng các bạn đến với bài hướng dẫn sử dụng        │ │
│ │ GitHub hôm nay. Trước hết, chúng ta hãy cùng nhìn vào  │ │
│ │ thanh điều hướng phía trên cùng...                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [Edit] [Delete] [Add After]                                │
│                                                             │
│ Segment 2/5:                                    [🔊 Play]  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Chào các bạn, chúng ta hãy cùng nhìn vào thanh điều    │ │
│ │ hướng ở phía trên cùng của trang web...                │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [Edit] [Delete] [Add After]                                │
│                                                             │
│ ... (3 more segments)                                      │
│                                                             │
│                    [Continue to TTS] [Back to Edit]        │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Job Type Detection & Routing Logic

#### 2.3.1 Smart Job Type Detection

```javascript
function detectJobType(userInput) {
  const indicators = {
    presentation: [
      "file extension: .pptx, .ppt",
      "keywords: slide, presentation, powerpoint, thuyết trình",
      "upload action detected",
    ],
    web: [
      "keywords: website, github, tutorial, hướng dẫn web",
      "URL detected in task",
      "no file upload",
    ],
    os: [
      "keywords: desktop, app, windows, phần mềm",
      "OS-specific terms: notepad, calculator, file explorer",
    ],
  };

  // Auto-detect based on file upload
  if (hasFileUpload && fileExtension === ".pptx") {
    return "presentation";
  }

  // Keyword analysis
  const taskLower = task.toLowerCase();
  let scores = {
    presentation: 0,
    web: 0,
    os: 0,
  };

  // Calculate scores...
  return highestScore;
}
```

#### 2.3.2 Queue Routing Matrix

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   Job Type      │     Queue       │     Worker      │   File Support  │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ web             │ web-queue       │ web-worker      │ None            │
│ presentation    │ presentation-q  │ presentation-w  │ .pptx, .ppt     │
│ office          │ office-queue    │ office-worker   │ .pptx, .pdf     │
│ os              │ os-queue        │ os-worker       │ None            │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

## 3. Autoscaler Integration Analysis

### 3.1 Current Autoscaler Role

```python
# From autoscaler.py analysis
class AutoScaler:
    def monitor_queues(self):
        """Monitor all queues and scale workers"""
        queues = ["web-queue", "presentation-queue", "office-queue", "os-queue"]

        for queue in queues:
            pending = redis.llen(queue)
            if pending > threshold:
                self.scale_up_worker(queue)
            elif pending == 0:
                self.scale_down_worker(queue)
```

### 3.2 Enhanced Job Routing in Autoscaler

```python
class SmartJobRouter:
    def route_job(self, job_data):
        """Enhanced job routing with validation"""

        # 1. Validate job type
        job_type = job_data.get('job_type')
        if not job_type:
            job_type = self.auto_detect_type(job_data)

        # 2. Check worker availability
        target_queue = self.get_queue_for_type(job_type)
        if not self.is_worker_available(target_queue):
            return self.queue_with_scaling(job_data, target_queue)

        # 3. Route to appropriate queue
        return self.submit_to_queue(job_data, target_queue)

    def auto_detect_type(self, job_data):
        """Auto-detect job type from content"""
        task = job_data.get('task', '').lower()
        config = job_data.get('config', {})

        # File-based detection
        if config.get('pptx_path'):
            return 'presentation'

        # Keyword-based detection
        web_keywords = ['github', 'website', 'web', 'browser', 'trang web']
        os_keywords = ['desktop', 'windows', 'app', 'phần mềm']

        if any(kw in task for kw in web_keywords):
            return 'web'
        elif any(kw in task for kw in os_keywords):
            return 'os'

        return 'web'  # default
```

## 4. Phase 2.5 Review System Design

### 4.1 Why Phase 2.5 is Critical

```
Problem: AI-generated narrations often have issues:
• Repetitive content (như đã thấy trong logs)
• Incorrect Vietnamese diacritics
• Poor timing/pacing
• Missing context

Solution: Human review before expensive TTS generation
• Save time: Fix text before audio generation
• Save cost: Avoid re-generating TTS
• Quality: Human oversight ensures better output
```

### 4.2 Review Interface Requirements

#### 4.2.1 Real-time Collaboration

```
┌─────────────────────────────────────────────────────────────┐
│ 👥 Collaborative Review (2 reviewers online)               │
├─────────────────────────────────────────────────────────────┤
│ Segment 3: [Being edited by User A] 🔒                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Bây giờ, hãy nhìn vào phần trung tâm của trang...      │ │
│ │ [User A is typing...] ⌨️                               │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 💬 Comments:                                               │
│ User B: "Nên thêm giải thích về Hero Section"              │
│ User A: "Đồng ý, đang sửa..."                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2.2 Audio Preview

```
┌─────────────────────────────────────────────────────────────┐
│ 🔊 Audio Preview (Edge TTS Sample)                         │
├─────────────────────────────────────────────────────────────┤
│ Text: "Chào mừng các bạn đến với bài hướng dẫn..."        │
│                                                             │
│ Voice: [banmai ▼] Speed: [Normal ▼] [🎵 Generate Sample]   │
│                                                             │
│ ▶️ ████████████████░░░░ 0:08 / 0:12                        │
│                                                             │
│ Quality: ⭐⭐⭐⭐⭐ (5/5) [👍 Approve] [👎 Regenerate]      │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Review Workflow States

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   PENDING   │───▶│  REVIEWING  │───▶│  APPROVED   │───▶│ TTS_READY   │
│  (Phase 2)  │    │ (Phase 2.5) │    │ (Phase 2.5) │    │ (Phase 3)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       └───────────▶│  REJECTED   │◀───────────┘
                    │ (Back to 2) │
                    └─────────────┘
```

## 5. Technical Implementation Priorities

### 5.1 Phase 1: Core UI (High Priority)

- [ ] Job creation form with smart type detection
- [ ] File upload for presentations (.pptx)
- [ ] Basic job monitoring dashboard
- [ ] Queue status visualization

### 5.2 Phase 2: Enhanced Routing (Medium Priority)

- [ ] Auto-detect job type from content
- [ ] Validate worker availability before submit
- [ ] Enhanced autoscaler with smart routing
- [ ] Error handling & fallback queues

### 5.3 Phase 3: Phase 2.5 Review System (High Priority)

- [ ] TTS script review interface
- [ ] Real-time text editing
- [ ] Audio preview with sample generation
- [ ] Approval/rejection workflow

### 5.4 Phase 4: Advanced Features (Low Priority)

- [ ] Collaborative review (multi-user)
- [ ] Template system for common tasks
- [ ] Batch job processing
- [ ] Analytics & usage tracking

## 6. User Experience Considerations

### 6.1 Error Prevention

```
• Smart defaults based on job type
• File validation before upload
• Real-time task description analysis
• Worker availability check before submit
```

### 6.2 Progress Transparency

```
• Clear phase indicators (1/6, 2/6, etc.)
• Estimated time remaining
• Detailed logs for debugging
• Pause/resume capability at Phase 2.5
```

### 6.3 Mobile Responsiveness

```
• Responsive design for monitoring
• Touch-friendly review interface
• Offline capability for completed jobs
• Push notifications for job completion
```

---

## Next Steps

1. **Implement Phase 2.5 Review Interface** - Most critical for quality
2. **Build Smart Job Router** - Improve user experience
3. **Create Monitoring Dashboard** - Essential for production use
4. **Add File Upload System** - Enable presentation workflows

**Stop Point**: Phase 2.5 implementation should be prioritized as it directly impacts video quality and user satisfaction.
