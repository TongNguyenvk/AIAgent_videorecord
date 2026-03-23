// Configuration
const BACKEND_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

// State
let currentJobId = null;
let ws = null;
let reviewScript = [];
let config = {
    tts_engine: 'edge',
    tts_voice: 'vi-VN-HoaiMyNeural',
    cdp_url: 'http://localhost:9222',
    padding_ms: 500,
    enable_review: true
};

// Pipeline steps
const PIPELINE_STEPS = [
    "Phase 1: The Scout (browser-use + narration)",
    "Phase 2: The Parser (config + tts_script)",
    "Phase 2.5: Review TTS Script",
    "Phase 3: Ground-Truth TTS (Edge/FPT)",
    "Phase 4: The Injector (exact pauses)",
    "Phase 5: The Execution (Webreel record)",
    "Phase 6: The Composer (ffmpeg trace-sync)",
];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initButtons();
    initSidebar();
    loadConfig();
    checkBackendHealth();
    loadHistory();
});

// Tab switching
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
    
    // Load data if needed
    if (tabName === 'history') {
        loadHistory();
    }
}

// Button handlers
function initButtons() {
    document.getElementById('generate-btn').addEventListener('click', handleGenerate);
    document.getElementById('cancel-btn').addEventListener('click', handleCancel);
    document.getElementById('continue-btn').addEventListener('click', handleContinueReview);
    document.getElementById('cancel-review-btn').addEventListener('click', handleCancel);
    document.getElementById('add-segment-btn').addEventListener('click', handleAddSegment);
}

// Sidebar handlers
function initSidebar() {
    document.getElementById('sidebar-toggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.add('open');
    });
    
    document.getElementById('sidebar-close').addEventListener('click', () => {
        document.getElementById('sidebar').classList.remove('open');
    });
    
    document.getElementById('save-config-btn').addEventListener('click', saveConfig);
}

// Load config from localStorage
function loadConfig() {
    const saved = localStorage.getItem('webreel-config');
    if (saved) {
        config = JSON.parse(saved);
    }
    
    document.getElementById('config-tts-engine').value = config.tts_engine;
    document.getElementById('config-voice').value = config.tts_voice;
    document.getElementById('config-cdp-url').value = config.cdp_url;
    document.getElementById('config-padding').value = config.padding_ms / 1000;
    document.getElementById('config-enable-review').checked = config.enable_review;
}

// Save config to localStorage
function saveConfig() {
    config.tts_engine = document.getElementById('config-tts-engine').value;
    config.tts_voice = document.getElementById('config-voice').value;
    config.cdp_url = document.getElementById('config-cdp-url').value;
    config.padding_ms = parseFloat(document.getElementById('config-padding').value) * 1000;
    config.enable_review = document.getElementById('config-enable-review').checked;
    
    localStorage.setItem('webreel-config', JSON.stringify(config));
    
    document.getElementById('sidebar').classList.remove('open');
    alert('Đã lưu cấu hình');
}

// Check backend health
async function checkBackendHealth() {
    const statusBadge = document.getElementById('backend-status');
    const statusText = statusBadge.querySelector('.status-text');
    
    try {
        const response = await fetch(`${BACKEND_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            
            // Check if server is shutting down
            if (data.is_shutting_down) {
                statusBadge.classList.remove('connected');
                statusBadge.classList.add('error');
                statusText.textContent = 'Backend: Đang tắt (đang reset...)';
                
                // Auto-reset shutdown flag
                try {
                    await fetch(`${BACKEND_URL}/api/admin/reset-shutdown`, {
                        method: 'POST'
                    });
                    console.log('Auto-reset shutdown flag');
                    
                    // Re-check health after reset
                    setTimeout(checkBackendHealth, 1000);
                } catch (e) {
                    console.error('Failed to reset shutdown flag:', e);
                }
            } else {
                statusBadge.classList.add('connected');
                statusBadge.classList.remove('error');
                statusText.textContent = 'Backend: Hoạt động';
            }
        } else {
            throw new Error('Backend not healthy');
        }
    } catch (error) {
        statusBadge.classList.remove('connected');
        statusBadge.classList.add('error');
        statusText.textContent = 'Backend: Không hoạt động';
    }
}

// Generate video
async function handleGenerate() {
    const task = document.getElementById('task-input').value.trim();
    const videoName = document.getElementById('video-name').value.trim() || 'demo';
    
    if (!task) {
        alert('Vui lòng nhập kịch bản');
        return;
    }
    
    const generateBtn = document.getElementById('generate-btn');
    generateBtn.disabled = true;
    generateBtn.textContent = 'Đang gửi...';
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/jobs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task,
                video_name: videoName,
                config: {
                    enable_tts: true,
                    tts_voice: config.tts_voice,
                    tts_engine: config.tts_engine,
                    cdp_url: config.cdp_url,
                    padding_ms: config.padding_ms,
                    enable_review: config.enable_review
                }
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            
            // If 503 (shutting down), try to reset and retry once
            if (response.status === 503) {
                console.log('Server shutting down, attempting auto-reset...');
                try {
                    await fetch(`${BACKEND_URL}/api/admin/reset-shutdown`, {
                        method: 'POST'
                    });
                    
                    // Wait a bit and retry
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    const retryResponse = await fetch(`${BACKEND_URL}/api/jobs`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            task,
                            video_name: videoName,
                            config: {
                                enable_tts: true,
                                tts_voice: config.tts_voice,
                                tts_engine: config.tts_engine,
                                cdp_url: config.cdp_url,
                                padding_ms: config.padding_ms,
                                enable_review: config.enable_review
                            }
                        })
                    });
                    
                    if (retryResponse.ok) {
                        const data = await retryResponse.json();
                        currentJobId = data.job_id;
                        
                        document.getElementById('progress-section').style.display = 'block';
                        document.getElementById('current-job-id').textContent = currentJobId;
                        connectWebSocket(currentJobId);
                        return;
                    }
                } catch (resetError) {
                    console.error('Auto-reset failed:', resetError);
                }
            }
            
            throw new Error(error.detail || 'Failed to submit job');
        }
        
        const data = await response.json();
        currentJobId = data.job_id;
        
        // Show progress section
        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('current-job-id').textContent = currentJobId;
        
        // Connect WebSocket
        connectWebSocket(currentJobId);
        
    } catch (error) {
        alert(`Lỗi: ${error.message}`);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Tạo Video';
    }
}

// WebSocket connection
function connectWebSocket(jobId) {
    if (ws) {
        ws.close();
    }
    
    ws = new WebSocket(`${WS_URL}/ws/${jobId}`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        document.getElementById('ws-status').textContent = 'WebSocket: Đã kết nối';
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleProgressUpdate(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        document.getElementById('ws-status').textContent = 'WebSocket: Lỗi kết nối';
    };
    
    ws.onclose = () => {
        console.log('WebSocket closed');
        document.getElementById('ws-status').textContent = 'WebSocket: Đã ngắt kết nối';
    };
}

// Handle progress updates
function handleProgressUpdate(data) {
    const status = data.status;
    const progress = data.progress;
    
    console.log('Progress update:', status, progress);
    
    // Check if job is done
    if (status === 'completed') {
        handleJobCompleted(data);
        return;
    }
    
    if (status === 'failed' || status === 'cancelled') {
        handleJobFailed(data);
        return;
    }
    
    // Update progress
    if (progress) {
        const phase = progress.current_phase;
        const message = progress.message;
        
        // Check if Phase 2.5 (review mode)
        if (phase === 2.5 && progress.tts_script) {
            showReviewUI(progress.tts_script);
            return;
        }
        
        // If we're past Phase 2.5, make sure progress section is visible
        if (phase > 2.5) {
            const reviewSection = document.getElementById('review-section');
            const progressSection = document.getElementById('progress-section');
            if (reviewSection.style.display !== 'none') {
                reviewSection.style.display = 'none';
                progressSection.style.display = 'block';
            }
        }
        
        // Map phase to step index
        let step = phase;
        if (phase > 2 && phase !== 2.5) {
            step = phase + 1; // Account for Phase 2.5
        } else if (phase === 2.5) {
            step = 3;
        }
        
        updateProgressUI(step, message);
    }
}

// Update progress UI
function updateProgressUI(step, message) {
    const total = PIPELINE_STEPS.length;
    const percentage = (step / total) * 100;
    
    // Update progress bar
    document.getElementById('progress-bar').style.width = `${percentage}%`;
    document.getElementById('progress-text').textContent = `${step}/${total}`;
    
    // Update steps
    const stepsContainer = document.getElementById('progress-steps');
    stepsContainer.innerHTML = '';
    
    PIPELINE_STEPS.forEach((label, index) => {
        const stepIndex = index + 1;
        const div = document.createElement('div');
        div.className = 'step-item';
        
        if (stepIndex < step) {
            div.classList.add('step-done');
        } else if (stepIndex === step) {
            div.classList.add('step-active');
        } else {
            div.classList.add('step-pending');
        }
        
        div.textContent = label;
        stepsContainer.appendChild(div);
    });
}

// Show review UI
function showReviewUI(ttsScript) {
    reviewScript = ttsScript;
    
    // Hide progress, show review
    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('review-section').style.display = 'block';
    
    renderReviewSegments();
}

// Render review segments
function renderReviewSegments() {
    const container = document.getElementById('review-segments');
    container.innerHTML = '';
    
    reviewScript.forEach((segment, index) => {
        const div = document.createElement('div');
        div.className = 'segment-item';
        div.innerHTML = `
            <div class="segment-header">
                <span class="segment-index">Đoạn ${index}</span>
                <div class="segment-actions">
                    <button class="btn btn-secondary" onclick="deleteSegment(${index})">Xóa</button>
                </div>
            </div>
            <textarea class="segment-textarea" id="segment-${index}">${segment.text}</textarea>
        `;
        container.appendChild(div);
    });
}

// Delete segment
window.deleteSegment = function(index) {
    if (confirm(`Xóa đoạn ${index}?`)) {
        reviewScript.splice(index, 1);
        // Re-index
        reviewScript.forEach((seg, i) => {
            seg.narration_index = i;
        });
        renderReviewSegments();
    }
};

// Add segment
function handleAddSegment() {
    const text = prompt('Nhập nội dung đoạn mới:');
    if (text && text.trim()) {
        reviewScript.push({
            text: text.trim(),
            narration_index: reviewScript.length
        });
        renderReviewSegments();
    }
}

// Continue after review
async function handleContinueReview() {
    const continueBtn = document.getElementById('continue-btn');
    continueBtn.disabled = true;
    continueBtn.textContent = 'Đang gửi...';
    
    try {
        // Collect all text from textareas (user may have edited without clicking save)
        reviewScript.forEach((segment, index) => {
            const textarea = document.getElementById(`segment-${index}`);
            if (textarea) {
                segment.text = textarea.value;
            }
        });
        
        const response = await fetch(`${BACKEND_URL}/api/jobs/${currentJobId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tts_script: reviewScript })
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit review');
        }
        
        // Hide review, show progress
        document.getElementById('review-section').style.display = 'none';
        document.getElementById('progress-section').style.display = 'block';
        
        // Update progress to Phase 3
        updateProgressUI(4, 'Đang tiếp tục pipeline...');
        
    } catch (error) {
        alert(`Lỗi: ${error.message}`);
        continueBtn.disabled = false;
        continueBtn.textContent = 'Tiếp tục tạo video';
    }
}

// Cancel job
async function handleCancel() {
    if (!confirm('Bạn có chắc muốn hủy job này?')) {
        return;
    }
    
    try {
        await fetch(`${BACKEND_URL}/api/jobs/${currentJobId}`, {
            method: 'DELETE'
        });
        
        // Close WebSocket
        if (ws) {
            ws.close();
        }
        
        // Hide sections
        document.getElementById('progress-section').style.display = 'none';
        document.getElementById('review-section').style.display = 'none';
        
        alert('Đã hủy job');
        
    } catch (error) {
        alert(`Lỗi: ${error.message}`);
    }
}

// Handle job completed
function handleJobCompleted(data) {
    if (ws) {
        ws.close();
    }
    
    // Hide progress section in create tab
    document.getElementById('progress-section').style.display = 'none';
    
    const result = data.result;
    if (result && result.video_path) {
        displayVideo(result.video_path, result.video_url);
        switchTab('result');
    }
    
    // Reset current job ID so user can create new video
    currentJobId = null;
}

// Handle job failed
function handleJobFailed(data) {
    if (ws) {
        ws.close();
    }
    
    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('review-section').style.display = 'none';
    
    const error = data.error || 'Job failed';
    alert(`Lỗi: ${error}`);
}

// Display video
function displayVideo(videoPath, videoUrl) {
    const container = document.getElementById('video-container');
    const fileName = videoPath.split(/[/\\]/).pop();
    
    container.innerHTML = `
        <video controls>
            <source src="${BACKEND_URL}${videoUrl}" type="video/mp4">
            Trình duyệt không hỗ trợ video.
        </video>
        <div class="video-info">
            <div class="info-item">
                <div class="info-label">File</div>
                <div class="info-value">${fileName}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Đường dẫn</div>
                <div class="info-value">${videoPath}</div>
            </div>
        </div>
    `;
}

// Load history
async function loadHistory() {
    const container = document.getElementById('history-list');
    container.innerHTML = '<p class="empty-state">Đang tải...</p>';
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/jobs?status=completed&limit=10`);
        const data = await response.json();
        
        if (data.jobs && data.jobs.length > 0) {
            container.innerHTML = '';
            data.jobs.forEach(job => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.innerHTML = `
                    <div class="history-date">${new Date(job.created_at).toLocaleString('vi-VN')}</div>
                    <div class="history-name">${job.video_name}</div>
                `;
                div.onclick = () => {
                    if (job.result && job.result.video_url) {
                        displayVideo(job.result.video_path, job.result.video_url);
                        switchTab('result');
                    }
                };
                container.appendChild(div);
            });
        } else {
            container.innerHTML = '<p class="empty-state">Chưa có video nào</p>';
        }
    } catch (error) {
        container.innerHTML = '<p class="empty-state">Lỗi khi tải lịch sử</p>';
    }
}
