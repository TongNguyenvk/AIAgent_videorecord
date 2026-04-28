# Audio Sync Optimization & Multi-Website Testing Plan

## Mục tiêu ngày mai

Tối ưu hóa luồng đồng bộ audio-video để đạt được timing chính xác và test trên nhiều loại trang web khác nhau để đảm bảo tính ổn định của hệ thống.

## 1. Tối ưu Audio Sync Engine

### 1.1 Phân tích vấn đề hiện tại

**Timing Issues đã phát hiện:**
- TTS audio thường dài hơn hoặc ngắn hơn thời gian dự kiến
- Pause timing không đồng bộ với video actions
- Audio overlap khi có nhiều segments liên tiếp
- Delay giữa action và narration không tự nhiên

**Root Causes:**
- FPT.AI TTS speed không consistent
- Timeline calculation không tính đến network latency
- Browser action duration varies by website complexity
- Audio preprocessing chưa optimize

### 1.2 Enhanced Audio Sync Algorithm

**Timing Calculation Improvements:**
```python
def calculate_precise_timing(steps, base_delay=300):
    timeline = []
    current_time = 0.0
    
    for step in steps:
        # Dynamic duration based on action complexity
        if step["action"] == "navigate":
            duration = 3.0 + estimate_page_load_time(step["url"])
        elif step["action"] == "type":
            char_count = len(step["text"])
            duration = char_count * 0.08 + 0.5  # More realistic typing
        elif step["action"] == "click":
            duration = 0.3 + estimate_element_complexity(step["selector"])
        
        timeline.append({
            "action": step["action"],
            "start_time": current_time,
            "duration": duration,
            "end_time": current_time + duration
        })
        
        current_time += duration + (base_delay / 1000.0)
    
    return timeline
```

### 1.3 Audio Preprocessing Pipeline

**TTS Optimization:**
- Pre-analyze text length vs expected duration
- Auto-adjust speech speed based on content density
- Add buffer time for complex explanations
- Implement audio stretching/compression for perfect sync

**Buffer Management:**
- Pre-action narration (1.5s before action)
- Post-action explanation (0.5s after action)
- Transition smoothing between segments
- Silence padding for natural flow

## 2. Multi-Website Testing Strategy

### 2.1 Website Categories for Testing

**Category A: Search Engines**
- Google.com - Standard search workflow
- Bing.com - Alternative search engine
- DuckDuckGo.com - Privacy-focused search
- Baidu.com - Chinese search engine (different UI patterns)

**Category B: Social Media Platforms**
- Facebook.com - Complex dynamic content
- Twitter/X.com - Real-time updates
- LinkedIn.com - Professional network
- Instagram.com - Image-focused platform

**Category C: E-commerce Sites**
- Amazon.com - Complex product search
- eBay.com - Auction-style interface
- Shopee.vn - Vietnamese e-commerce
- Tiki.vn - Local marketplace

**Category D: Educational Platforms**
- Khan Academy - Video-based learning
- Coursera.org - Course enrollment flow
- edX.org - University courses
- Udemy.com - Skill-based learning

**Category E: Government/Official Sites**
- Wikipedia.org - Information lookup
- GitHub.com - Code repository navigation
- Stack Overflow - Q&A interaction
- Reddit.com - Forum-style discussion
**Category F: Banking/Financial**
- VietcomBank.com.vn - Vietnamese banking
- PayPal.com - Payment processing
- Coinbase.com - Cryptocurrency platform
- Binance.com - Trading interface

**Category G: News/Media**
- BBC.com - International news
- CNN.com - US news network
- VnExpress.net - Vietnamese news
- YouTube.com - Video platform

**Category H: Productivity Tools**
- Gmail.com - Email management
- Google Drive - File storage
- Notion.so - Note-taking app
- Trello.com - Project management

### 2.2 Test Scenarios per Category

**Basic Workflow Tests:**
1. **Search & Navigate**: Enter query, click results, browse content
2. **Form Filling**: Registration, login, contact forms
3. **Content Creation**: Post, comment, upload, edit
4. **Shopping Flow**: Search product, add to cart, checkout process
5. **Account Management**: Profile setup, settings, preferences

**Advanced Interaction Tests:**
1. **Dynamic Content**: Infinite scroll, lazy loading, real-time updates
2. **Modal Dialogs**: Popups, confirmations, multi-step wizards
3. **Drag & Drop**: File uploads, reordering, interactive elements
4. **Keyboard Shortcuts**: Hotkeys, navigation, accessibility
5. **Mobile Responsive**: Different viewport sizes, touch interactions

### 2.3 Testing Metrics & Success Criteria

**Audio Sync Quality Metrics:**
- Timing accuracy: ±200ms tolerance
- Audio clarity: No distortion or clipping
- Narration relevance: 95% contextually appropriate
- Flow naturalness: Smooth transitions between segments

**Website Compatibility Metrics:**
- Selector success rate: >90% across all sites
- Action completion rate: >95% for standard workflows
- Error recovery: Graceful handling of failed actions
- Performance consistency: <10% variance in execution time

**User Experience Metrics:**
- Video comprehension: Clear explanation of each step
- Educational value: Viewers can replicate the process
- Engagement level: Natural pacing and rhythm
- Accessibility: Proper contrast, readable text, clear audio

## 3. Implementation Roadmap

### Phase 1: Core Audio Sync Improvements (Morning)

**Tasks:**
1. Implement enhanced timing calculation algorithm
2. Add audio preprocessing pipeline
3. Create buffer management system
4. Test with existing video samples

**Expected Outcomes:**
- 50% improvement in timing accuracy
- Smoother audio transitions
- Reduced audio-video desync issues

### Phase 2: Website Testing Framework (Afternoon)

**Tasks:**
1. Create automated test suite for multiple websites
2. Implement website-specific optimizations
3. Add error handling for different UI patterns
4. Document compatibility matrix

**Expected Outcomes:**
- Comprehensive compatibility report
- Identified edge cases and solutions
- Optimized selectors for major platforms

### Phase 3: Integration & Validation (Evening)

**Tasks:**
1. Integrate improvements into main pipeline
2. Run full test suite across all website categories
3. Generate sample videos for each category
4. Performance benchmarking and optimization

**Expected Outcomes:**
- Production-ready audio sync system
- Validated compatibility across 20+ websites
- Performance metrics and optimization recommendations

## 4. Technical Implementation Details

### 4.1 Audio Sync Optimizer Module

```python
class AudioSyncOptimizer:
    def __init__(self, target_fps=60, buffer_ms=200):
        self.target_fps = target_fps
        self.buffer_ms = buffer_ms
        self.frame_duration = 1000 / target_fps  # ms per frame
    
    def optimize_timeline(self, video_timeline, tts_script):
        # Analyze video timing
        video_events = self.extract_video_events(video_timeline)
        
        # Optimize TTS timing
        optimized_tts = self.adjust_tts_timing(tts_script, video_events)
        
        # Add buffer zones
        final_timeline = self.add_buffer_zones(optimized_tts)
        
        return final_timeline
    
    def adjust_tts_timing(self, tts_script, video_events):
        # Implementation for precise timing adjustment
        pass
```

### 4.2 Website Testing Framework

```python
class WebsiteTestSuite:
    def __init__(self):
        self.test_sites = self.load_test_sites()
        self.results = {}
    
    async def run_comprehensive_test(self):
        for category, sites in self.test_sites.items():
            category_results = []
            
            for site in sites:
                result = await self.test_website(site)
                category_results.append(result)
            
            self.results[category] = category_results
        
        return self.generate_report()
    
    async def test_website(self, site_config):
        # Implementation for individual website testing
        pass
```

## 5. Expected Deliverables

### 5.1 Code Deliverables
- Enhanced `audio_sync_optimizer.py` module
- Updated `ai_reviewer.py` with timing improvements
- New `website_test_suite.py` for automated testing
- Improved `bu_to_webreel.py` with website-specific optimizations

### 5.2 Documentation Deliverables
- Website compatibility matrix
- Audio sync optimization guide
- Testing methodology documentation
- Performance benchmarking report

### 5.3 Sample Outputs
- 5 optimized video samples from different website categories
- Before/after comparison showing sync improvements
- Error handling demonstrations
- Performance metrics dashboard

## 6. Success Metrics

**Quantitative Goals:**
- Audio sync accuracy: <200ms deviation
- Website compatibility: 90%+ success rate
- Processing speed: <2 minutes per video
- Error recovery: 95% graceful handling

**Qualitative Goals:**
- Natural narration flow
- Clear step-by-step explanations
- Professional video quality
- User-friendly error messages

## 7. Risk Mitigation

**Potential Risks:**
1. Website anti-bot measures blocking automation
2. TTS API rate limiting or quality issues
3. Complex dynamic content causing selector failures
4. Performance degradation with optimization overhead

**Mitigation Strategies:**
1. Implement rotating user agents and delays
2. Fallback TTS providers and caching mechanisms
3. Advanced selector strategies and fallback chains
4. Performance profiling and selective optimization

## 8. Next Steps After Completion

1. Integration with production pipeline
2. User acceptance testing with real scenarios
3. Performance optimization based on metrics
4. Documentation updates and training materials
5. Preparation for advanced features (subtitles, multiple languages)

---

**Timeline:** 1 full day (8 hours)
**Priority:** High - Critical for production readiness
**Dependencies:** Completed parser and AI reviewer modules
**Success Criteria:** All tests pass, audio sync <200ms deviation, 90%+ website compatibility

## 9. Kịch bản tác vụ cho video thành phẩm

### 9.0 Giới hạn và tác vụ phù hợp

**Tác vụ CÓ THỂ thực hiện (Browser-only):**
- Tìm kiếm và browse nội dung
- Click, scroll, navigate giữa các trang
- Điền form (không submit thật)
- Xem chi tiết sản phẩm, bài viết
- Browse menu, category, filter
- Xem preview, demo, interface

**Tác vụ KHÔNG THỂ thực hiện:**
- Upload file từ máy tính
- Gửi email thật sự
- Thực hiện thanh toán thật
- Tạo account mới (cần verification)
- Download file về máy
- Truy cập camera/microphone
- Tương tác với OS (outside browser)

### 9.1 Video Demo Category A: Search Engines

**Task 1: Google Search Tutorial**
```
"Vào Google.com và tìm kiếm thông tin về Python programming. Sau đó click vào kết quả đầu tiên, scroll xuống để đọc nội dung và xem các section khác nhau."
```

**Task 2: Bing Advanced Search**
```
"Truy cập Bing.com, sử dụng tính năng tìm kiếm nâng cao để tìm hình ảnh về machine learning, scroll qua các kết quả và click vào một hình ảnh để xem chi tiết."
```

**Task 3: DuckDuckGo Privacy Search**
```
"Vào DuckDuckGo.com, tìm kiếm về privacy tools, scroll xuống để xem nhiều kết quả hơn, sau đó click vào tab Images."
```

### 9.2 Video Demo Category B: Social Media

**Task 4: Facebook Page Navigation**
```
"Truy cập Facebook.com, tìm kiếm trang của Microsoft, click vào trang, scroll xuống để xem các bài post gần nhất và tương tác."
```

**Task 5: LinkedIn Profile Search**
```
"Vào LinkedIn.com, tìm kiếm profile của các Software Engineer tại Google, scroll qua danh sách kết quả và click vào một profile để xem chi tiết."
```

**Task 6: Twitter/X Content Discovery**
```
"Truy cập X.com, tìm kiếm hashtag #AI, scroll xuống để xem nhiều tweet hơn, sau đó click vào tab Latest."
```

### 9.3 Video Demo Category C: E-commerce

**Task 7: Amazon Product Search**
```
"Vào Amazon.com, tìm kiếm laptop gaming, scroll qua danh sách sản phẩm, sử dụng filter để lọc theo giá từ 1000-2000 USD, scroll xuống và xem chi tiết một sản phẩm."
```

**Task 8: Shopee Vietnam Shopping**
```
"Truy cập Shopee.vn, tìm kiếm điện thoại iPhone, scroll qua các sản phẩm, sắp xếp theo giá từ thấp đến cao, scroll xuống và xem chi tiết sản phẩm đầu tiên."
```

**Task 9: eBay Auction Browse**
```
"Vào eBay.com, tìm kiếm vintage camera, scroll qua danh sách, lọc theo Auction items, scroll xuống và xem chi tiết một sản phẩm đang đấu giá."
```

### 9.4 Video Demo Category D: Educational Platforms

**Task 10: Khan Academy Course Browse**
```
"Truy cập KhanAcademy.org, tìm kiếm khóa học về Calculus, click vào khóa học, scroll xuống để xem syllabus và các video lessons."
```

**Task 11: Coursera Course Enrollment**
```
"Vào Coursera.org, tìm kiếm khóa học Machine Learning của Stanford, scroll xuống để xem thông tin chi tiết về course content và instructors."
```

**Task 12: GitHub Repository Exploration**
```
"Truy cập GitHub.com, tìm kiếm repository React, sắp xếp theo Most stars, click vào repository đầu tiên, scroll xuống để đọc README file và xem code examples."
```

### 9.5 Video Demo Category E: Productivity Tools

**Task 13: Gmail Interface Navigation**
```
"Vào Gmail.com, click vào nút Compose để mở giao diện soạn email, điền subject 'Test Email' và xem các tùy chọn formatting."
```

**Task 14: Google Drive Interface Browse**
```
"Truy cập Google Drive, click vào nút New để xem menu tạo mới, sau đó browse qua các folder có sẵn và xem chi tiết một file."
```

**Task 15: Notion Interface Exploration**
```
"Vào Notion.so, browse qua các template có sẵn, click vào Meeting Notes template để xem preview và explore các tính năng formatting."
```

### 9.6 Video Demo Category F: News & Media

**Task 16: YouTube Video Search**
```
"Truy cập YouTube.com, tìm kiếm video về AI tutorial, scroll qua danh sách video, lọc theo upload time trong tuần qua, scroll xuống và click vào một video để xem thông tin."
```

**Task 17: BBC News Browse**
```
"Vào BBC.com, click vào section Technology, scroll xuống để đọc headline của nhiều bài báo, click vào một bài để xem chi tiết và scroll để đọc nội dung."
```

**Task 18: VnExpress News Navigation**
```
"Truy cập VnExpress.net, vào mục Công nghệ, scroll qua các bài viết, tìm bài viết về AI hoặc công nghệ mới, click vào và scroll để đọc toàn bộ bài."
```

### 9.7 Video Demo Category G: Complex Applications

**Task 19: Trello Interface Navigation**
```
"Vào Trello.com, browse qua các template board có sẵn, click vào một template để xem chi tiết và explore các tính năng của Trello."
```

**Task 20: PayPal Interface Browse**
```
"Truy cập PayPal.com, click vào Send Money để xem giao diện, explore các tùy chọn payment mà không thực hiện giao dịch thật."
```

### 9.8 Kịch bản bổ sung phù hợp với browser-only

**Task 21: Stack Overflow Q&A Browse**
```
"Vào StackOverflow.com, tìm kiếm câu hỏi về React hooks, click vào câu hỏi có nhiều upvote nhất và đọc các câu trả lời."
```

**Task 22: Wikipedia Deep Dive**
```
"Truy cập Wikipedia.org, tìm kiếm về Artificial Intelligence, click vào các link liên quan và explore cấu trúc bài viết."
```

**Task 23: Reddit Community Browse**
```
"Vào Reddit.com, browse subreddit r/programming, xem các post hot nhất và click vào comments để đọc thảo luận."
```

**Task 24: Medium Article Reading**
```
"Truy cập Medium.com, tìm kiếm bài viết về Machine Learning, click vào bài viết và scroll để đọc nội dung."
```

**Task 25: Coursera Course Preview**
```
"Vào Coursera.org, browse các khóa học về Data Science, click vào khóa học để xem syllabus và preview video."
```

### 9.9 Kịch bản TTS cho từng video

**Cấu trúc narration chuẩn:**

**Mở đầu (3-5 giây):**
```
"Chào mừng bạn đến với hướng dẫn [tên tác vụ]. Hôm nay chúng ta sẽ học cách [mô tả ngắn gọn]."
```

**Các bước thực hiện (theo timeline):**
```
"Đầu tiên, chúng ta truy cập vào [tên website]."
"Tiếp theo, tìm kiếm [nội dung] trong ô tìm kiếm."
"Bây giờ, click vào [element] để [mục đích]."
"Cuối cùng, chúng ta [hành động cuối] để hoàn thành tác vụ."
```

**Kết thúc (2-3 giây):**
```
"Vậy là chúng ta đã hoàn thành [tên tác vụ]. Cảm ơn bạn đã theo dõi!"
```

### 9.9 Technical Specifications cho video thành phẩm

**Video Quality:**
- Resolution: 1920x1080 (Full HD)
- Frame rate: 60 FPS
- Bitrate: 5000 kbps
- Codec: H.264

**Audio Quality:**
- Sample rate: 44.1 kHz
- Bitrate: 128 kbps
- Codec: AAC
- Voice: FPT.AI "banmai" (female, professional)

**Timing Requirements:**
- Total duration: 30-90 seconds per video
- Audio sync tolerance: ±200ms
- Pause between actions: 500-1000ms
- Narration lead time: 1.5s before action

**Visual Elements:**
- Cursor animation: Smooth bezier curves
- Click effects: Subtle highlight circles
- Zoom level: 1.5x for better visibility
- HUD display: Action labels when needed

### 9.10 Automated Testing Script

```python
# test_video_production.py
import asyncio
from run_pipeline_unified_chrome import run_unified_pipeline

DEMO_TASKS = [
    {
        "name": "google-search-python",
        "task": "Vào Google.com và tìm kiếm thông tin về Python programming. Sau đó click vào kết quả đầu tiên và scroll để đọc nội dung.",
        "expected_duration": 45,
        "category": "search"
    },
    {
        "name": "amazon-laptop-search", 
        "task": "Vào Amazon.com, tìm kiếm laptop gaming, sử dụng filter để lọc theo giá từ 1000-2000 USD và xem chi tiết sản phẩm.",
        "expected_duration": 60,
        "category": "ecommerce"
    },
    {
        "name": "youtube-ai-tutorial",
        "task": "Truy cập YouTube.com, tìm kiếm video về AI tutorial, click vào video đầu tiên để xem thông tin chi tiết.",
        "expected_duration": 50,
        "category": "media"
    },
    {
        "name": "github-react-repo",
        "task": "Truy cập GitHub.com, tìm kiếm repository React, click vào repository đầu tiên và scroll để xem README file.",
        "expected_duration": 50,
        "category": "development"
    },
    {
        "name": "shopee-iphone-search",
        "task": "Truy cập Shopee.vn, tìm kiếm điện thoại iPhone, sắp xếp theo giá và xem chi tiết sản phẩm đầu tiên.",
        "expected_duration": 55,
        "category": "ecommerce-vn"
    }
]

async def generate_demo_videos():
    results = []
    
    for demo in DEMO_TASKS:
        print(f"Generating video: {demo['name']}")
        
        try:
            video_path = await run_unified_pipeline(
                task=demo["task"],
                video_name=demo["name"],
                cdp_url="http://localhost:9222"
            )
            
            results.append({
                "name": demo["name"],
                "status": "success",
                "path": video_path,
                "category": demo["category"]
            })
            
        except Exception as e:
            results.append({
                "name": demo["name"], 
                "status": "failed",
                "error": str(e),
                "category": demo["category"]
            })
    
    return results

if __name__ == "__main__":
    results = asyncio.run(generate_demo_videos())
    
    # Generate report
    success_count = len([r for r in results if r["status"] == "success"])
    total_count = len(results)
    
    print(f"\n=== Demo Video Generation Report ===")
    print(f"Success: {success_count}/{total_count}")
    print(f"Success Rate: {success_count/total_count*100:.1f}%")
    
    for result in results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"{status_icon} {result['name']} ({result['category']})")
        if result["status"] == "failed":
            print(f"   Error: {result['error']}")
```

### 9.11 Quality Assurance Checklist

**Pre-production:**
- [ ] Chrome debug server running on port 9222
- [ ] FPT.AI API key configured and tested
- [ ] All target websites accessible
- [ ] Audio sync optimizer calibrated

**During production:**
- [ ] Monitor timing accuracy for each video
- [ ] Check audio quality and clarity
- [ ] Verify selector success rate
- [ ] Log any errors or edge cases

**Post-production:**
- [ ] Review all generated videos manually
- [ ] Verify audio-video synchronization
- [ ] Check narration accuracy and naturalness
- [ ] Test video playback on different devices
- [ ] Generate performance metrics report

**Delivery:**
- [ ] 5 high-quality demo videos
- [ ] Compatibility matrix document
- [ ] Performance benchmarking report
- [ ] Updated documentation with findings
- [ ] Recommendations for production deployment