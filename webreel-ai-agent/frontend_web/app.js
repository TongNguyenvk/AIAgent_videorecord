// Configuration
const BACKEND_URL = "http://localhost:8000";
const WS_URL = "ws://localhost:8000";

// Enhanced State Management
let activeJobs = new Map(); // job_id -> job_data
let pollingIntervals = new Map(); // job_id -> interval_id
let currentJobId = null;
let ws = null;
let reviewScript = [];
let config = {
  tts_engine: "edge",
  tts_voice: "vi-VN-HoaiMyNeural",
  cdp_url: "http://localhost:9222",
  padding_ms: 500,
  enable_review: true,
};

// Job Manager Class - Implements Phase 2.5 Architecture
class JobManager {
  constructor() {
    this.activeJobs = new Map();
    this.pollingIntervals = new Map();
    this.loadJobsFromStorage();
  }

  async createJob(jobData) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(jobData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to create job");
      }

      const result = await response.json();
      const jobId = result.job_id;

      // Add to active jobs
      this.activeJobs.set(jobId, {
        id: jobId,
        status: "created",
        phase: "0",
        progress: 0,
        created_at: new Date().toISOString(),
        task: jobData.task,
        job_type: this.detectJobType(jobData),
      });

      // Save to localStorage
      this.addJobToStorage(jobId);

      // Start polling
      this.startPolling(jobId);

      return jobId;
    } catch (error) {
      console.error("Failed to create job:", error);
      throw error;
    }
  }

  detectJobType(jobData) {
    const task = jobData.task.toLowerCase();
    const config = jobData.config || {};

    // File-based detection
    if (config.pptx_path) {
      return "presentation";
    }

    // Keyword-based detection
    const webKeywords = [
      "github",
      "website",
      "web",
      "browser",
      "trang web",
      "google.com",
    ];
    const osKeywords = ["desktop", "windows", "app", "phần mềm", "notepad", "calculator"];

    if (webKeywords.some((kw) => task.includes(kw))) {
      return "web";
    } else if (osKeywords.some((kw) => task.includes(kw))) {
      return "os";
    }

    return "web"; // default
  }

  startPolling(jobId) {
    // Clear existing interval if any
    if (this.pollingIntervals.has(jobId)) {
      clearInterval(this.pollingIntervals.get(jobId));
    }

    // Polling every 3 seconds
    const interval = setInterval(async () => {
      try {
        const status = await this.getJobStatus(jobId);
        this.updateJobState(jobId, status);

        // Stop polling if job completed or failed
        if (["completed", "failed", "abandoned"].includes(status.status)) {
          this.stopPolling(jobId);
        }

        // Trigger UI update
        this.notifyJobUpdate(jobId, status);
      } catch (error) {
        console.error(`Polling error for job ${jobId}:`, error);
        // Continue polling even on errors (network issues)
      }
    }, 3000);

    this.pollingIntervals.set(jobId, interval);
  }

  stopPolling(jobId) {
    if (this.pollingIntervals.has(jobId)) {
      clearInterval(this.pollingIntervals.get(jobId));
      this.pollingIntervals.delete(jobId);
    }
  }

  async getJobStatus(jobId) {
    const response = await fetch(`${BACKEND_URL}/api/jobs/${jobId}/status`);
    if (!response.ok) {
      throw new Error(`Failed to get job status: ${response.status}`);
    }
    const result = await response.json();
    return result.job;
  }

  async getJobScript(jobId) {
    const response = await fetch(`${BACKEND_URL}/api/jobs/${jobId}/script`);
    if (!response.ok) {
      throw new Error(`Failed to get job script: ${response.status}`);
    }
    const result = await response.json();
    return result.script;
  }

  async approveScript(jobId, approvedScript) {
    const response = await fetch(`${BACKEND_URL}/api/jobs/${jobId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ script: approvedScript }),
    });

    if (!response.ok) {
      throw new Error(`Failed to approve script: ${response.status}`);
    }

    return response.json();
  }

  updateJobState(jobId, status) {
    if (this.activeJobs.has(jobId)) {
      const job = this.activeJobs.get(jobId);
      Object.assign(job, status);
      this.activeJobs.set(jobId, job);
    }
  }

  notifyJobUpdate(jobId, status) {
    // Trigger custom event for UI updates
    window.dispatchEvent(
      new CustomEvent("jobUpdate", {
        detail: { jobId, status },
      }),
    );
  }

  // LocalStorage management
  addJobToStorage(jobId) {
    const jobs = this.getJobsFromStorage();
    if (!jobs.includes(jobId)) {
      jobs.push(jobId);
      localStorage.setItem("webreel_jobs", JSON.stringify(jobs));
    }
  }

  getJobsFromStorage() {
    const jobs = localStorage.getItem("webreel_jobs");
    return jobs ? JSON.parse(jobs) : [];
  }

  loadJobsFromStorage() {
    const jobs = this.getJobsFromStorage();
    jobs.forEach((jobId) => {
      // Only start polling for non-completed jobs
      this.getJobStatus(jobId)
        .then((status) => {
          if (!["completed", "failed", "abandoned"].includes(status.status)) {
            this.startPolling(jobId);
          }
          this.activeJobs.set(jobId, status);
        })
        .catch((error) => {
          console.error(`Failed to load job ${jobId}:`, error);
          // Remove invalid job from storage
          this.removeJobFromStorage(jobId);
        });
    });
  }

  removeJobFromStorage(jobId) {
    const jobs = this.getJobsFromStorage();
    const filtered = jobs.filter((id) => id !== jobId);
    localStorage.setItem("webreel_jobs", JSON.stringify(filtered));
  }

  getAllActiveJobs() {
    return Array.from(this.activeJobs.values());
  }

  getJob(jobId) {
    return this.activeJobs.get(jobId);
  }
}

// Global job manager instance
let jobManager = null;

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
document.addEventListener("DOMContentLoaded", () => {
  // Initialize job manager
  jobManager = new JobManager();

  initNavigation();
  initJobTypeSelector();
  initFileUpload();
  initFormHandlers();
  initModalHandlers();
  initJobUpdateListener();
  loadConfig();
  checkBackendHealth();

  // Load initial data
  updateJobsDashboard();
  loadCompletedVideos();
});

// Navigation
function initNavigation() {
  const navTabs = document.querySelectorAll(".nav-tab");
  navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const tabName = tab.dataset.tab;
      switchTab(tabName);
    });
  });
}

function switchTab(tabName) {
  // Update nav tabs
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });

  // Update tab panels
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${tabName}-tab`);
  });

  // Load data if needed
  if (tabName === "dashboard") {
    updateJobsDashboard();
  } else if (tabName === "completed") {
    loadCompletedVideos();
  }
}

// Job Type Selector
function initJobTypeSelector() {
  const jobTypeBtns = document.querySelectorAll(".job-type-btn");
  jobTypeBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      // Update active state
      jobTypeBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Handle file upload visibility
      const jobType = btn.dataset.type;
      const fileUploadSection = document.getElementById("file-upload-section");
      const taskHint = document.getElementById("task-hint");

      if (jobType === "presentation") {
        fileUploadSection.style.display = "block";
        taskHint.innerHTML =
          "📊 Upload your PowerPoint file and optionally describe the presentation content";
      } else {
        fileUploadSection.style.display = "none";

        if (jobType === "web") {
          taskHint.innerHTML =
            "🌐 Example: \"Go to google.com, search for 'Python programming' and show the results\"";
        } else if (jobType === "desktop") {
          taskHint.innerHTML =
            '🖥️ Example: "Open Notepad, type some text, and save the file"';
        }
      }
    });
  });
}

// File Upload
function initFileUpload() {
  const fileUploadArea = document.getElementById("file-upload-area");
  const fileInput = document.getElementById("pptx-file");

  fileUploadArea.addEventListener("click", () => {
    fileInput.click();
  });

  fileUploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    fileUploadArea.style.borderColor = "var(--primary-color)";
    fileUploadArea.style.background = "#eff6ff";
  });

  fileUploadArea.addEventListener("dragleave", (e) => {
    e.preventDefault();
    fileUploadArea.style.borderColor = "var(--border-color)";
    fileUploadArea.style.background = "";
  });

  fileUploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    fileUploadArea.style.borderColor = "var(--border-color)";
    fileUploadArea.style.background = "";

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      fileInput.files = files;
      updateFileUploadDisplay(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      updateFileUploadDisplay(e.target.files[0]);
    }
  });
}

function updateFileUploadDisplay(file) {
  const uploadText = document.querySelector(".upload-text");
  const uploadIcon = document.querySelector(".upload-icon");

  if (file) {
    uploadIcon.textContent = "📄";
    uploadText.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
  } else {
    uploadIcon.textContent = "📁";
    uploadText.textContent = "Choose PPTX File or drag & drop";
  }
}

// Form Handlers
function initFormHandlers() {
  document
    .getElementById("create-video-btn")
    .addEventListener("click", handleCreateVideo);
  document
    .getElementById("refresh-btn")
    .addEventListener("click", () => updateJobsDashboard());

  // Auto-refresh toggle
  const autoRefreshToggle = document.getElementById("auto-refresh");
  autoRefreshToggle.addEventListener("change", (e) => {
    if (e.target.checked) {
      startAutoRefresh();
    } else {
      stopAutoRefresh();
    }
  });

  // Start auto-refresh by default
  startAutoRefresh();
}

let autoRefreshInterval = null;

function startAutoRefresh() {
  if (autoRefreshInterval) return;

  autoRefreshInterval = setInterval(() => {
    const currentTab = document.querySelector(".nav-tab.active").dataset.tab;
    if (currentTab === "dashboard") {
      updateJobsDashboard();
    }
  }, 5000); // Refresh every 5 seconds
}

function stopAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }
}

// Modal Handlers
function initModalHandlers() {
  // Review modal
  document.getElementById("close-review").addEventListener("click", () => {
    hideModal("review-modal");
  });

  document
    .getElementById("continue-tts-btn")
    .addEventListener("click", handleContinueReview);
  document.getElementById("back-edit-btn").addEventListener("click", () => {
    hideModal("review-modal");
  });

  // Progress modal
  document.getElementById("close-progress").addEventListener("click", () => {
    hideModal("progress-modal");
  });

  document
    .getElementById("cancel-job-btn")
    .addEventListener("click", handleCancelCurrentJob);
}

function showModal(modalId) {
  document.getElementById(modalId).style.display = "flex";
  document.body.style.overflow = "hidden";
}

function hideModal(modalId) {
  document.getElementById(modalId).style.display = "none";
  document.body.style.overflow = "";
}

// Listen for job updates
function initJobUpdateListener() {
  window.addEventListener("jobUpdate", (event) => {
    const { jobId, status } = event.detail;

    // Update current job if it matches
    if (jobId === currentJobId) {
      handleJobStatusUpdate(status);
    }

    // Update jobs dashboard
    updateJobsDashboard();
  });
}

function handleJobStatusUpdate(status) {
  if (status.status === "pending_review") {
    // Show review modal
    showReviewModal(currentJobId, status);
  } else if (status.status === "completed") {
    // Hide progress modal and show success
    hideModal("progress-modal");
    showSuccessMessage("Video created successfully!");
    loadCompletedVideos();
  } else if (status.status === "failed") {
    // Hide progress modal and show error
    hideModal("progress-modal");
    showErrorMessage(status.error || "Job failed");
  } else {
    // Update progress modal
    updateProgressModal(status);
  }
}

// Tab switching
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabName = btn.dataset.tab;
      switchTab(tabName);
    });
  });
}

function switchTab(tabName) {
  // Update buttons
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });

  // Update content
  document.querySelectorAll(".tab-content").forEach((content) => {
    content.classList.toggle("active", content.id === `${tabName}-tab`);
  });

  // Load data if needed
  if (tabName === "history") {
    loadHistory();
  } else if (tabName === "dashboard") {
    updateJobsDashboard();
  }
}

// Button handlers
function initButtons() {
  document.getElementById("generate-btn").addEventListener("click", handleGenerate);
  document.getElementById("cancel-btn").addEventListener("click", handleCancel);
  document.getElementById("continue-btn").addEventListener("click", handleContinueReview);
  document.getElementById("cancel-review-btn").addEventListener("click", handleCancel);
  document.getElementById("add-segment-btn").addEventListener("click", handleAddSegment);

  // Job type selection handler
  document
    .getElementById("job-type-select")
    .addEventListener("change", handleJobTypeChange);

  // Task input handler for auto-detection
  document.getElementById("task-input").addEventListener("input", handleTaskInputChange);
}

function handleJobTypeChange() {
  const jobType = document.getElementById("job-type-select").value;
  const fileUploadSection = document.getElementById("file-upload-section");
  const jobTypeHint = document.getElementById("job-type-hint");

  if (jobType === "presentation") {
    fileUploadSection.style.display = "block";
    jobTypeHint.textContent = "📊 Upload file PowerPoint để tạo video thuyết trình";
  } else {
    fileUploadSection.style.display = "none";

    if (jobType === "web") {
      jobTypeHint.textContent =
        "🌐 Mô tả các bước thao tác trên website (GitHub, Google, v.v.)";
    } else if (jobType === "os") {
      jobTypeHint.textContent =
        "🖥️ Mô tả các thao tác với ứng dụng desktop (Notepad, Calculator, v.v.)";
    } else {
      jobTypeHint.textContent =
        "💡 Hệ thống sẽ tự động phát hiện loại video dựa trên nội dung";
    }
  }
}

function handleTaskInputChange() {
  const jobTypeSelect = document.getElementById("job-type-select");
  const task = document.getElementById("task-input").value.toLowerCase();
  const jobTypeHint = document.getElementById("job-type-hint");

  if (jobTypeSelect.value !== "auto") return;

  // Auto-detect and show hint
  const webKeywords = [
    "github",
    "website",
    "web",
    "browser",
    "trang web",
    "google.com",
    "facebook.com",
  ];
  const osKeywords = [
    "desktop",
    "windows",
    "app",
    "phần mềm",
    "notepad",
    "calculator",
    "file explorer",
  ];

  if (webKeywords.some((kw) => task.includes(kw))) {
    jobTypeHint.innerHTML =
      "🤖 <strong>Phát hiện:</strong> Web Tutorial - Hướng dẫn sử dụng website";
  } else if (osKeywords.some((kw) => task.includes(kw))) {
    jobTypeHint.innerHTML =
      "🤖 <strong>Phát hiện:</strong> Desktop App Demo - Hướng dẫn ứng dụng desktop";
  } else if (task.trim()) {
    jobTypeHint.innerHTML = "🤖 <strong>Phát hiện:</strong> Web Tutorial (mặc định)";
  } else {
    jobTypeHint.textContent =
      "💡 Hệ thống sẽ tự động phát hiện loại video dựa trên nội dung";
  }
}

// Sidebar handlers
function initSidebar() {
  document.getElementById("sidebar-toggle").addEventListener("click", () => {
    document.getElementById("sidebar").classList.add("open");
  });

  document.getElementById("sidebar-close").addEventListener("click", () => {
    document.getElementById("sidebar").classList.remove("open");
  });

  document.getElementById("save-config-btn").addEventListener("click", saveConfig);
}

// Load config from localStorage
function loadConfig() {
  const saved = localStorage.getItem("webreel-config");
  if (saved) {
    config = JSON.parse(saved);
  }

  document.getElementById("config-tts-engine").value = config.tts_engine;
  document.getElementById("config-voice").value = config.tts_voice;
  document.getElementById("config-cdp-url").value = config.cdp_url;
  document.getElementById("config-padding").value = config.padding_ms / 1000;
  document.getElementById("config-enable-review").checked = config.enable_review;
}

// Save config to localStorage
function saveConfig() {
  config.tts_engine = document.getElementById("config-tts-engine").value;
  config.tts_voice = document.getElementById("config-voice").value;
  config.cdp_url = document.getElementById("config-cdp-url").value;
  config.padding_ms = parseFloat(document.getElementById("config-padding").value) * 1000;
  config.enable_review = document.getElementById("config-enable-review").checked;

  localStorage.setItem("webreel-config", JSON.stringify(config));

  document.getElementById("sidebar").classList.remove("open");
  alert("Đã lưu cấu hình");
}

// Check backend health
async function checkBackendHealth() {
  const statusBadge = document.getElementById("backend-status");
  const statusText = statusBadge.querySelector(".status-text");

  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    if (response.ok) {
      const data = await response.json();

      // Check if server is shutting down
      if (data.is_shutting_down) {
        statusBadge.classList.remove("connected");
        statusBadge.classList.add("error");
        statusText.textContent = "Backend: Đang tắt (đang reset...)";

        // Auto-reset shutdown flag
        try {
          await fetch(`${BACKEND_URL}/api/admin/reset-shutdown`, {
            method: "POST",
          });
          console.log("Auto-reset shutdown flag");

          // Re-check health after reset
          setTimeout(checkBackendHealth, 1000);
        } catch (e) {
          console.error("Failed to reset shutdown flag:", e);
        }
      } else {
        statusBadge.classList.add("connected");
        statusBadge.classList.remove("error");
        statusText.textContent = "Backend: Hoạt động";
      }
    } else {
      throw new Error("Backend not healthy");
    }
  } catch (error) {
    statusBadge.classList.remove("connected");
    statusBadge.classList.add("error");
    statusText.textContent = "Backend: Không hoạt động";
  }
}

// Create Video Handler
async function handleCreateVideo() {
  const taskInput = document.getElementById("task-input");
  const task = taskInput.value.trim();

  if (!task) {
    showErrorMessage("Please enter a task description");
    return;
  }

  // Get selected job type
  const selectedJobType = document.querySelector(".job-type-btn.active");
  const jobType = selectedJobType ? selectedJobType.dataset.type : "web";

  // Get file if presentation type
  const pptxFile = document.getElementById("pptx-file").files[0];
  if (jobType === "presentation" && !pptxFile) {
    showErrorMessage("Please select a PowerPoint file");
    return;
  }

  // Get settings
  const voice = document.getElementById("voice-select").value;
  const engine = document.getElementById("engine-select").value;
  const padding = parseInt(document.getElementById("padding-select").value);

  const createBtn = document.getElementById("create-video-btn");
  const originalText = createBtn.innerHTML;
  createBtn.disabled = true;
  createBtn.innerHTML =
    '<span class="btn-icon">⏳</span><span class="btn-text">Creating...</span>';

  try {
    // Prepare job data
    const jobData = {
      task,
      job_type: jobType,
      config: {
        enable_tts: true,
        tts_voice: voice,
        tts_engine: engine,
        padding_ms: padding,
        enable_review: true,
      },
    };

    // Handle file upload for presentation
    if (pptxFile) {
      // TODO: Implement file upload
      jobData.config.pptx_file = pptxFile.name;
      jobData.config.pptx_size = pptxFile.size;
    }

    const jobId = await jobManager.createJob(jobData);
    currentJobId = jobId;

    // Show progress modal
    showProgressModal(jobId);

    // Clear form
    taskInput.value = "";
    document.getElementById("pptx-file").value = "";
    updateFileUploadDisplay(null);

    // Switch to dashboard tab
    switchTab("dashboard");

    showSuccessMessage("Job created successfully! Check the dashboard for progress.");
  } catch (error) {
    showErrorMessage(`Error: ${error.message}`);
  } finally {
    createBtn.disabled = false;
    createBtn.innerHTML = originalText;
  }
}

// Progress Modal
function showProgressModal(jobId) {
  document.getElementById("progress-job-id").textContent = jobId.substring(0, 8) + "...";

  // Reset progress
  updateProgressBar(0);
  document.getElementById("progress-phase").textContent = "Initializing...";

  // Clear steps
  const stepsContainer = document.getElementById("progress-steps");
  stepsContainer.innerHTML = "";

  showModal("progress-modal");
}

function updateProgressModal(status) {
  const progress = status.progress || 0;
  const phase = status.phase || "0";
  const message = status.message || "Processing...";

  updateProgressBar(progress);
  document.getElementById("progress-phase").textContent = `Phase ${phase}: ${message}`;

  // Update steps
  updateProgressSteps(parseFloat(phase));
}

function updateProgressBar(percentage) {
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");

  progressBar.style.width = `${percentage}%`;
  progressText.textContent = `${percentage}%`;
}

const PIPELINE_STEPS = [
  { phase: 1, label: "Phase 1: Scout (browser-use + narration)", icon: "🔍" },
  { phase: 2, label: "Phase 2: Parser (config + tts_script)", icon: "⚙️" },
  { phase: 2.5, label: "Phase 2.5: Review TTS Script", icon: "📝" },
  { phase: 3, label: "Phase 3: Ground-Truth TTS (Edge/FPT)", icon: "🔊" },
  { phase: 4, label: "Phase 4: Injector (exact pauses)", icon: "⏱️" },
  { phase: 5, label: "Phase 5: Execution (Webreel record)", icon: "🎬" },
  { phase: 6, label: "Phase 6: Composer (ffmpeg trace-sync)", icon: "🎞️" },
];

function updateProgressSteps(currentPhase) {
  const stepsContainer = document.getElementById("progress-steps");
  stepsContainer.innerHTML = "";

  PIPELINE_STEPS.forEach((step) => {
    const stepDiv = document.createElement("div");
    stepDiv.className = "progress-step";

    if (step.phase < currentPhase) {
      stepDiv.classList.add("completed");
    } else if (step.phase === currentPhase) {
      stepDiv.classList.add("active");
    } else {
      stepDiv.classList.add("pending");
    }

    stepDiv.innerHTML = `
            <span class="step-icon">${step.icon}</span>
            <span class="step-label">${step.label}</span>
        `;

    stepsContainer.appendChild(stepDiv);
  });
}

// Review Modal
async function showReviewModal(jobId, status) {
  try {
    const script = await jobManager.getJobScript(jobId);

    document.getElementById("review-job-id").textContent = jobId.substring(0, 8) + "...";

    renderReviewSegments(script.segments || []);
    showModal("review-modal");
  } catch (error) {
    showErrorMessage(`Failed to load script: ${error.message}`);
  }
}

function renderReviewSegments(segments) {
  const container = document.getElementById("segments-container");
  container.innerHTML = "";

  segments.forEach((segment, index) => {
    const segmentDiv = document.createElement("div");
    segmentDiv.className = "segment-item";
    segmentDiv.innerHTML = `
            <div class="segment-header">
                <div class="segment-number">
                    Segment ${index + 1}/5:
                    <button class="btn btn-secondary btn-icon" onclick="playSegment(${index})">🔊</button>
                </div>
                <div class="segment-actions">
                    <button class="btn btn-secondary" onclick="editSegment(${index})">Edit</button>
                    <button class="btn btn-secondary" onclick="deleteSegment(${index})">Delete</button>
                    <button class="btn btn-secondary" onclick="addAfterSegment(${index})">Add After</button>
                </div>
            </div>
            <textarea class="segment-text" id="segment-${index}" rows="3">${segment.text}</textarea>
        `;
    container.appendChild(segmentDiv);
  });

  // Store segments globally for later use
  reviewScript = segments;
}

// Segment Actions
window.playSegment = function (index) {
  // TODO: Implement audio preview
  showInfoMessage(`Playing segment ${index + 1} (Preview not implemented yet)`);
};

window.editSegment = function (index) {
  const textarea = document.getElementById(`segment-${index}`);
  textarea.focus();
  textarea.select();
};

window.deleteSegment = function (index) {
  if (confirm(`Delete segment ${index + 1}?`)) {
    reviewScript.splice(index, 1);
    renderReviewSegments(reviewScript);
  }
};

window.addAfterSegment = function (index) {
  const text = prompt("Enter new segment text:");
  if (text && text.trim()) {
    reviewScript.splice(index + 1, 0, {
      text: text.trim(),
      narration_index: index + 1,
    });
    renderReviewSegments(reviewScript);
  }
};

// Continue Review
async function handleContinueReview() {
  const continueBtn = document.getElementById("continue-tts-btn");
  const originalText = continueBtn.innerHTML;
  continueBtn.disabled = true;
  continueBtn.innerHTML = '<span class="btn-text">Submitting...</span>';

  try {
    // Collect updated text from textareas
    reviewScript.forEach((segment, index) => {
      const textarea = document.getElementById(`segment-${index}`);
      if (textarea) {
        segment.text = textarea.value;
      }
    });

    await jobManager.approveScript(currentJobId, reviewScript);

    hideModal("review-modal");
    showProgressModal(currentJobId);

    showSuccessMessage("Script approved! Continuing to TTS phase...");
  } catch (error) {
    showErrorMessage(`Failed to approve script: ${error.message}`);
    continueBtn.disabled = false;
    continueBtn.innerHTML = originalText;
  }
}

// Cancel Current Job
async function handleCancelCurrentJob() {
  if (!currentJobId) return;

  if (!confirm("Are you sure you want to cancel this job?")) {
    return;
  }

  try {
    await cancelJob(currentJobId);
    hideModal("progress-modal");
    currentJobId = null;
  } catch (error) {
    showErrorMessage(`Failed to cancel job: ${error.message}`);
  }
}

// WebSocket connection
function connectWebSocket(jobId) {
  if (ws) {
    ws.close();
  }

  ws = new WebSocket(`${WS_URL}/ws/${jobId}`);

  ws.onopen = () => {
    console.log("WebSocket connected");
    document.getElementById("ws-status").textContent = "WebSocket: Đã kết nối";
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleProgressUpdate(data);
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
    document.getElementById("ws-status").textContent = "WebSocket: Lỗi kết nối";
  };

  ws.onclose = () => {
    console.log("WebSocket closed");
    document.getElementById("ws-status").textContent = "WebSocket: Đã ngắt kết nối";
  };
}

// Handle progress updates
function handleProgressUpdate(data) {
  const status = data.status;
  const progress = data.progress;

  console.log("Progress update:", status, progress);

  // Check if job is done
  if (status === "completed") {
    handleJobCompleted(data);
    return;
  }

  if (status === "failed" || status === "cancelled") {
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
      const reviewSection = document.getElementById("review-section");
      const progressSection = document.getElementById("progress-section");
      if (reviewSection.style.display !== "none") {
        reviewSection.style.display = "none";
        progressSection.style.display = "block";
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
  document.getElementById("progress-bar").style.width = `${percentage}%`;
  document.getElementById("progress-text").textContent = `${step}/${total}`;

  // Update steps
  const stepsContainer = document.getElementById("progress-steps");
  stepsContainer.innerHTML = "";

  PIPELINE_STEPS.forEach((label, index) => {
    const stepIndex = index + 1;
    const div = document.createElement("div");
    div.className = "step-item";

    if (stepIndex < step) {
      div.classList.add("step-done");
    } else if (stepIndex === step) {
      div.classList.add("step-active");
    } else {
      div.classList.add("step-pending");
    }

    div.textContent = label;
    stepsContainer.appendChild(div);
  });
}

// Show review UI - Enhanced with Job Manager
function showReviewUI(ttsScript) {
  reviewScript = ttsScript;

  // Hide progress, show review
  document.getElementById("progress-section").style.display = "none";
  document.getElementById("review-section").style.display = "block";

  renderReviewSegments();
}

// Jobs Dashboard - Enhanced with new design
function updateJobsDashboard() {
  const activeJobs = jobManager
    .getAllActiveJobs()
    .filter((job) => !["completed", "failed", "abandoned"].includes(job.status));
  const completedJobs = jobManager
    .getAllActiveJobs()
    .filter((job) => ["completed", "failed", "abandoned"].includes(job.status));

  // Update counts
  document.getElementById("active-count").textContent = activeJobs.length;
  document.getElementById("completed-count").textContent = completedJobs.length;

  // Render active jobs
  const activeJobsList = document.getElementById("active-jobs-list");
  if (activeJobs.length === 0) {
    activeJobsList.innerHTML = '<div class="empty-state">No active jobs</div>';
  } else {
    activeJobsList.innerHTML = activeJobs.map((job) => createJobCard(job)).join("");

    // Add event listeners
    activeJobs.forEach((job) => {
      const viewBtn = document.getElementById(`view-job-${job.id}`);
      const cancelBtn = document.getElementById(`cancel-job-${job.id}`);

      viewBtn?.addEventListener("click", () => viewJob(job.id));
      cancelBtn?.addEventListener("click", () => cancelJob(job.id));
    });
  }

  // Render completed jobs
  const completedJobsList = document.getElementById("completed-jobs-list");
  if (completedJobs.length === 0) {
    completedJobsList.innerHTML = '<div class="empty-state">No completed jobs</div>';
  } else {
    completedJobsList.innerHTML = completedJobs
      .map((job) => createCompletedJobCard(job))
      .join("");

    // Add event listeners
    completedJobs.forEach((job) => {
      const downloadBtn = document.getElementById(`download-job-${job.id}`);
      const viewBtn = document.getElementById(`view-job-${job.id}`);
      const deleteBtn = document.getElementById(`delete-job-${job.id}`);

      downloadBtn?.addEventListener("click", () => downloadVideo(job.id));
      viewBtn?.addEventListener("click", () => viewVideo(job.id));
      deleteBtn?.addEventListener("click", () => deleteJob(job.id));
    });
  }
}

function createJobCard(job) {
  const shortId = job.id.substring(0, 8);
  const progress = job.progress || 0;
  const phase = job.phase || "0";
  const status = job.status || "unknown";

  // Determine status info
  let statusClass = "status-running";
  let statusIcon = "🎬";
  let statusText = `Phase ${phase}`;

  if (status === "pending_review") {
    statusClass = "status-review";
    statusIcon = "📝";
    statusText = "Phase 2.5: Review";
  } else if (status.includes("phase_1")) {
    statusIcon = "🔍";
    statusText = "Phase 1: Scout";
  } else if (status.includes("phase_2")) {
    statusIcon = "⚙️";
    statusText = "Phase 2: Parser";
  } else if (status.includes("phase_3")) {
    statusIcon = "🔊";
    statusText = "Phase 3: TTS";
  } else if (status.includes("phase_4")) {
    statusIcon = "⏱️";
    statusText = "Phase 4: Injector";
  } else if (status.includes("phase_5")) {
    statusIcon = "🎬";
    statusText = "Phase 5: Execution";
  } else if (status.includes("phase_6")) {
    statusIcon = "🎞️";
    statusText = "Phase 6: Composer";
  }

  return `
        <div class="job-card">
            <div class="job-header">
                <div class="job-info">
                    <div class="job-title">
                        ${getJobTypeIcon(job.job_type)} ${job.task ? job.task.substring(0, 60) + "..." : "Untitled Job"}
                    </div>
                    <div class="job-meta">
                        ID: ${shortId} | ${job.job_type || "web"} worker | ${getTimeAgo(job.created_at)}
                    </div>
                </div>
                <div class="job-status ${statusClass}">
                    ${statusText}
                </div>
            </div>
            
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${progress}%"></div>
                <span class="progress-text">${progress}%</span>
            </div>
            
            <div class="job-actions">
                <button id="view-job-${job.id}" class="btn btn-secondary">
                    <span class="btn-icon">👁️</span>
                    <span class="btn-text">View</span>
                </button>
                <button id="cancel-job-${job.id}" class="btn btn-secondary">
                    <span class="btn-icon">❌</span>
                    <span class="btn-text">Cancel</span>
                </button>
            </div>
        </div>
    `;
}

function createCompletedJobCard(job) {
  const shortId = job.id.substring(0, 8);
  const status = job.status || "unknown";

  let statusClass = "status-completed";
  let statusIcon = "✅";
  let statusText = "Completed";

  if (status === "failed") {
    statusClass = "status-failed";
    statusIcon = "❌";
    statusText = "Failed";
  } else if (status === "abandoned") {
    statusClass = "status-failed";
    statusIcon = "⚠️";
    statusText = "Abandoned";
  }

  return `
        <div class="job-card">
            <div class="job-header">
                <div class="job-info">
                    <div class="job-title">
                        ${statusIcon} ${job.task ? job.task.substring(0, 60) + "..." : "Untitled Job"}
                    </div>
                    <div class="job-meta">
                        ID: ${shortId} | ${job.job_type || "web"} worker | ${getTimeAgo(job.created_at)}
                        ${job.result?.video_path ? `| 📹 ${job.result.video_path.split("/").pop()} (${formatFileSize(job.result.file_size)})` : ""}
                    </div>
                </div>
                <div class="job-status ${statusClass}">
                    ${statusText}
                </div>
            </div>
            
            <div class="job-actions">
                ${
                  status === "completed"
                    ? `
                    <button id="download-job-${job.id}" class="btn btn-primary">
                        <span class="btn-icon">📥</span>
                        <span class="btn-text">Download</span>
                    </button>
                    <button id="view-job-${job.id}" class="btn btn-secondary">
                        <span class="btn-icon">👁️</span>
                        <span class="btn-text">View</span>
                    </button>
                `
                    : ""
                }
                <button id="delete-job-${job.id}" class="btn btn-secondary">
                    <span class="btn-icon">🗑️</span>
                    <span class="btn-text">Delete</span>
                </button>
            </div>
        </div>
    `;
}

function getJobTypeIcon(jobType) {
  switch (jobType) {
    case "web":
      return "🌐";
    case "presentation":
      return "📊";
    case "desktop":
      return "🖥️";
    default:
      return "🎬";
  }
}

function getTimeAgo(dateString) {
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins} min ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
}

function formatFileSize(bytes) {
  if (!bytes) return "Unknown size";

  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

// Job Actions
async function viewJob(jobId) {
  try {
    const job = jobManager.getJob(jobId);
    if (!job) {
      showErrorMessage("Job not found");
      return;
    }

    currentJobId = jobId;

    if (job.status === "pending_review") {
      await showReviewModal(jobId, job);
    } else {
      showProgressModal(jobId);
      updateProgressModal(job);
    }
  } catch (error) {
    showErrorMessage(`Failed to view job: ${error.message}`);
  }
}

async function cancelJob(jobId) {
  if (!confirm("Are you sure you want to cancel this job?")) {
    return;
  }

  try {
    await fetch(`${BACKEND_URL}/api/jobs/${jobId}`, {
      method: "DELETE",
    });

    // Stop polling
    jobManager.stopPolling(jobId);

    // Remove from active jobs
    jobManager.activeJobs.delete(jobId);
    jobManager.removeJobFromStorage(jobId);

    // Update dashboard
    updateJobsDashboard();

    showSuccessMessage("Job cancelled successfully");
  } catch (error) {
    showErrorMessage(`Failed to cancel job: ${error.message}`);
  }
}

async function downloadVideo(jobId) {
  try {
    const job = jobManager.getJob(jobId);
    if (!job || !job.result?.video_url) {
      showErrorMessage("Video not available for download");
      return;
    }

    // Create download link
    const link = document.createElement("a");
    link.href = `${BACKEND_URL}${job.result.video_url}`;
    link.download = job.result.video_path.split("/").pop();
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showSuccessMessage("Download started");
  } catch (error) {
    showErrorMessage(`Failed to download video: ${error.message}`);
  }
}

async function viewVideo(jobId) {
  // TODO: Implement video viewer modal
  showInfoMessage("Video viewer not implemented yet");
}

async function deleteJob(jobId) {
  if (
    !confirm("Are you sure you want to delete this job? This action cannot be undone.")
  ) {
    return;
  }

  try {
    // TODO: Implement job deletion API
    jobManager.activeJobs.delete(jobId);
    jobManager.removeJobFromStorage(jobId);

    updateJobsDashboard();
    showSuccessMessage("Job deleted successfully");
  } catch (error) {
    showErrorMessage(`Failed to delete job: ${error.message}`);
  }
}

// Completed Videos
function loadCompletedVideos() {
  const completedJobs = jobManager
    .getAllActiveJobs()
    .filter((job) => job.status === "completed" && job.result?.video_path);

  const videosList = document.getElementById("completed-videos-list");

  if (completedJobs.length === 0) {
    videosList.innerHTML = '<div class="empty-state">No completed videos yet</div>';
    return;
  }

  videosList.innerHTML = completedJobs.map((job) => createVideoCard(job)).join("");

  // Add event listeners
  completedJobs.forEach((job) => {
    const downloadBtn = document.getElementById(`download-video-${job.id}`);
    const viewBtn = document.getElementById(`view-video-${job.id}`);

    downloadBtn?.addEventListener("click", () => downloadVideo(job.id));
    viewBtn?.addEventListener("click", () => viewVideo(job.id));
  });
}

function createVideoCard(job) {
  const fileName = job.result.video_path.split("/").pop();
  const fileSize = formatFileSize(job.result.file_size);

  return `
        <div class="video-card">
            <div class="video-thumbnail">
                🎬
            </div>
            <div class="video-info">
                <div class="video-title">${fileName}</div>
                <div class="video-meta">
                    ${fileSize} | ${getTimeAgo(job.created_at)} | ${job.job_type || "web"} tutorial
                </div>
                <div class="video-actions">
                    <button id="download-video-${job.id}" class="btn btn-primary">
                        <span class="btn-icon">📥</span>
                        <span class="btn-text">Download</span>
                    </button>
                    <button id="view-video-${job.id}" class="btn btn-secondary">
                        <span class="btn-icon">👁️</span>
                        <span class="btn-text">View</span>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Utility Functions
function showSuccessMessage(message) {
  showToast(message, "success");
}

function showErrorMessage(message) {
  showToast(message, "error");
}

function showInfoMessage(message) {
  showToast(message, "info");
}

function showToast(message, type = "info") {
  // Create toast element
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
        <span class="toast-icon">${getToastIcon(type)}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;

  // Add to page
  let toastContainer = document.getElementById("toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toast-container";
    toastContainer.className = "toast-container";
    document.body.appendChild(toastContainer);
  }

  toastContainer.appendChild(toast);

  // Auto remove after 5 seconds
  setTimeout(() => {
    if (toast.parentElement) {
      toast.remove();
    }
  }, 5000);
}

function getToastIcon(type) {
  switch (type) {
    case "success":
      return "✅";
    case "error":
      return "❌";
    case "warning":
      return "⚠️";
    default:
      return "ℹ️";
  }
}

// Load Config (simplified)
function loadConfig() {
  const saved = localStorage.getItem("webreel-config");
  if (saved) {
    config = JSON.parse(saved);

    // Apply to form
    document.getElementById("voice-select").value =
      config.tts_voice || "vi-VN-HoaiMyNeural";
    document.getElementById("engine-select").value = config.tts_engine || "edge";
    document.getElementById("padding-select").value = config.padding_ms || 300;
  }
}

// Check Backend Health
async function checkBackendHealth() {
  const statusIndicator = document.getElementById("backend-status");
  const statusText = statusIndicator.querySelector(".status-text");

  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    if (response.ok) {
      statusIndicator.classList.add("connected");
      statusIndicator.classList.remove("error");
      statusText.textContent = "Backend: Online";
    } else {
      throw new Error("Backend not healthy");
    }
  } catch (error) {
    statusIndicator.classList.remove("connected");
    statusIndicator.classList.add("error");
    statusText.textContent = "Backend: Offline";
  }
}

// Render review segments
function renderReviewSegments() {
  const container = document.getElementById("review-segments");
  container.innerHTML = "";

  reviewScript.forEach((segment, index) => {
    const div = document.createElement("div");
    div.className = "segment-item";
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
window.deleteSegment = function (index) {
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
  const text = prompt("Nhập nội dung đoạn mới:");
  if (text && text.trim()) {
    reviewScript.push({
      text: text.trim(),
      narration_index: reviewScript.length,
    });
    renderReviewSegments();
  }
}

// Continue after review - Enhanced with Job Manager
async function handleContinueReview() {
  const continueBtn = document.getElementById("continue-btn");
  continueBtn.disabled = true;
  continueBtn.textContent = "Đang gửi...";

  try {
    // Collect all text from textareas (user may have edited without clicking save)
    reviewScript.forEach((segment, index) => {
      const textarea = document.getElementById(`segment-${index}`);
      if (textarea) {
        segment.text = textarea.value;
      }
    });

    await jobManager.approveScript(currentJobId, reviewScript);

    // Hide review, show progress
    document.getElementById("review-section").style.display = "none";
    document.getElementById("progress-section").style.display = "block";

    // Update progress to Phase 3
    updateProgressUI(4, "Đang tiếp tục pipeline...");
  } catch (error) {
    alert(`Lỗi: ${error.message}`);
    continueBtn.disabled = false;
    continueBtn.textContent = "Tiếp tục tạo video";
  }
}

// Cancel job
async function handleCancel() {
  if (!confirm("Bạn có chắc muốn hủy job này?")) {
    return;
  }

  try {
    await fetch(`${BACKEND_URL}/api/jobs/${currentJobId}`, {
      method: "DELETE",
    });

    // Close WebSocket
    if (ws) {
      ws.close();
    }

    // Hide sections
    document.getElementById("progress-section").style.display = "none";
    document.getElementById("review-section").style.display = "none";

    alert("Đã hủy job");
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
  document.getElementById("progress-section").style.display = "none";

  const result = data.result;
  if (result && result.video_path) {
    displayVideo(result.video_path, result.video_url);
    switchTab("result");
  }

  // Reset current job ID so user can create new video
  currentJobId = null;
}

// Handle job failed
function handleJobFailed(data) {
  if (ws) {
    ws.close();
  }

  document.getElementById("progress-section").style.display = "none";
  document.getElementById("review-section").style.display = "none";

  const error = data.error || "Job failed";
  alert(`Lỗi: ${error}`);
}

// Display video
function displayVideo(videoPath, videoUrl) {
  const container = document.getElementById("video-container");
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
  const container = document.getElementById("history-list");
  container.innerHTML = '<p class="empty-state">Đang tải...</p>';

  try {
    const response = await fetch(`${BACKEND_URL}/api/jobs?status=completed&limit=10`);
    const data = await response.json();

    if (data.jobs && data.jobs.length > 0) {
      container.innerHTML = "";
      data.jobs.forEach((job) => {
        const div = document.createElement("div");
        div.className = "history-item";
        div.innerHTML = `
                    <div class="history-date">${new Date(job.created_at).toLocaleString("vi-VN")}</div>
                    <div class="history-name">${job.video_name}</div>
                `;
        div.onclick = () => {
          if (job.result && job.result.video_url) {
            displayVideo(job.result.video_path, job.result.video_url);
            switchTab("result");
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
