export type VideoStatus =
  | "pending"
  | "queued"
  | "running"
  | "processing"
  | "pending_review"
  | "completed"
  | "failed"
  | "cancelled";

export interface Video {
  id: string | number;
  title: string;
  status: VideoStatus;
  duration?: string;
  date: string;
  thumbnail?: string | null;
  video_url?: string;
  jobId?: string;
  progress?: JobProgress | null;
  error?: string | null;
}

export interface JobProgress {
  current_phase?: number;
  phase_name?: string;
  message?: string;
}

export interface JobDetail {
  job_id: string;
  status: VideoStatus;
  task: string;
  video_name: string;
  config: Record<string, unknown>;
  job_type?: string;
  progress?: JobProgress | null;
  result?: {
    video_path?: string;
    video_url?: string;
    duration_seconds?: number | null;
  } | null;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

// Dung bien moi truong Vite, fallback ve localhost khi dev
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function fetchVideos(): Promise<Video[]> {
  try {
    const res = await fetch(`${API_BASE}/jobs/`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch videos");
    const data = await res.json();

    // Map response cua FastAPI thanh chuan UI (data.jobs)
    return data.jobs.map((job: any) => ({
      id: job.job_id,
      title: job.video_name || job.task?.slice(0, 35) + "...",
      status: job.status,
      date: new Date(job.created_at).toLocaleString(),
      video_url: job.result?.video_url,
      duration: job.result?.duration_seconds ? `${job.result.duration_seconds}s` : "--",
      progress: job.progress || null,
      error: job.error || null,
    }));
  } catch (error) {
    console.error("API Error: Backend offline or CORS issue.", error);
    return [];
  }
}

export async function createVideo(data: {
  prompt: string;
  job_type: string;
  tts_engine: string;
  tts_voice: string;
  padding_ms: number;
  enable_tts: boolean;
  enable_review: boolean;
  file?: File;
  // V4 OS Worker fields
  app_type?: string;
  browser_url?: string;
}): Promise<Video> {
  let res;

  if (data.file) {
    const formData = new FormData();
    formData.append("file", data.file);
    formData.append("task", data.prompt);
    formData.append("tts_engine", data.tts_engine);
    formData.append("tts_voice", data.tts_voice);
    formData.append("padding_ms", String(data.padding_ms));
    formData.append("enable_review", String(data.enable_review));

    // V4: Add app_type and browser_url if present
    if (data.app_type) {
      formData.append("app_type", data.app_type);
    }
    if (data.browser_url) {
      formData.append("browser_url", data.browser_url);
    }

    const token = localStorage.getItem("token");

    // Route to correct endpoint based on job type
    const endpoint =
      data.job_type === "presentation"
        ? `${API_BASE}/upload-pptx-gg`
        : `${API_BASE}/jobs/upload-file`; // V4 OS Worker endpoint

    res = await fetch(endpoint, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
  } else {
    const payload = {
      task: data.prompt,
      job_type: data.job_type,
      config: {
        tts_engine: data.tts_engine,
        tts_voice: data.tts_voice,
        padding_ms: data.padding_ms,
        enable_tts: data.enable_tts,
        enable_review: data.enable_review,
        // V4 OS Worker config
        ...(data.app_type && { app_type: data.app_type }),
        ...(data.browser_url && { browser_url: data.browser_url }),
      },
    };

    res = await fetch(`${API_BASE}/queue/submit`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Create job failed");
  }

  const result = await res.json();
  return {
    id: result.job_id,
    title: data.prompt.slice(0, 35) + "...",
    status: result.status || "pending",
    date: new Date().toISOString(),
  };
}

// Lay chi tiet 1 job (dung cho dialog xem chi tiet)
export async function getJobDetail(jobId: string): Promise<JobDetail> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to get job detail");
  return res.json();
}

// Lay TTS script de review (Phase 2.5)
export async function getJobScript(jobId: string) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/script`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to get job script");
  const data = await res.json();
  // Backend tra { script: { segments: [...], ... } }
  return data.script;
}

// Gui script da duyet de tiep tuc pipeline
export async function approveScript(jobId: string, ttsScript: any[]) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/review`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ tts_script: ttsScript }),
  });
  if (!res.ok) throw new Error("Failed to approve script");
  return res.json();
}

// Tao URL download video (dung endpoint /api/jobs/{id}/video)
export function getVideoDownloadUrl(jobId: string): string {
  return `${API_BASE}/jobs/${jobId}/video`;
}

// URL xem truoc video (stream qua static files)
export function getVideoPreviewUrl(videoUrl: string | undefined): string | null {
  if (!videoUrl) return null;
  // video_url tu backend da la duong dan tuong doi /videos/...
  // Can ghep voi backend host
  const backendHost = API_BASE.replace("/api", "");
  if (videoUrl.startsWith("http")) return videoUrl;
  return `${backendHost}${videoUrl}`;
}

// Admin API functions
export interface AdminUser {
  user_id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  tier: string;
  status: string;
  email_verified: boolean;
  quota: {
    videos_per_month: number;
    videos_used_this_month: number;
  };
  created_at: string;
  last_login?: string;
}

export interface AdminStats {
  jobs: {
    total: number;
    by_status: Record<string, number>;
  };
  users: {
    total: number;
    active: number;
    suspended: number;
    by_tier: {
      free: number;
      pro: number;
      enterprise: number;
    };
    by_role: {
      admin: number;
      user: number;
    };
  };
}

export async function fetchAllUsers(): Promise<AdminUser[]> {
  const res = await fetch(`${API_BASE}/admin/users`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch users");
  const data = await res.json();
  return data.users;
}

export async function fetchAllJobs(): Promise<Video[]> {
  const res = await fetch(`${API_BASE}/admin/jobs`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch all jobs");
  const data = await res.json();

  return data.jobs.map((job: any) => ({
    id: job.job_id,
    title: job.video_name || job.task?.slice(0, 35) + "...",
    status: job.status,
    date: new Date(job.created_at).toLocaleString(),
    video_url: job.result?.video_url,
    duration: job.result?.duration_seconds ? `${job.result.duration_seconds}s` : "--",
    user_id: job.user_id,
  }));
}

export async function fetchAdminStats(): Promise<AdminStats> {
  const res = await fetch(`${API_BASE}/admin/stats`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function updateUserTier(
  userId: string,
  tier: string,
  videosPerMonth?: number,
) {
  const res = await fetch(
    `${API_BASE}/admin/users/${userId}/tier?tier=${tier}${videosPerMonth ? `&videos_per_month=${videosPerMonth}` : ""}`,
    {
      method: "PUT",
      headers: getAuthHeaders(),
    },
  );
  if (!res.ok) throw new Error("Failed to update user tier");
  return res.json();
}

export async function suspendUser(userId: string, reason: string) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}/suspend`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error("Failed to suspend user");
  return res.json();
}

export async function activateUser(userId: string) {
  const res = await fetch(`${API_BASE}/admin/users/${userId}/activate`, {
    method: "PUT",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to activate user");
  return res.json();
}

// Browser Session Management API functions
export interface BrowserSession {
  worker_type: string;
  last_login: string | null;
  days_since_login: number | null;
  needs_refresh: boolean;
  warning_level: "ok" | "warning" | "critical";
}

export interface VNCUrls {
  web: {
    url: string;
    port: number;
    worker: string;
  };
  presentation: {
    url: string;
    port: number;
    worker: string;
  };
}

export async function fetchBrowserSessions(): Promise<BrowserSession[]> {
  const res = await fetch(`${API_BASE}/browser/sessions`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch browser sessions");
  return res.json();
}

export async function updateBrowserSession(workerType: string, lastLogin: Date) {
  const res = await fetch(`${API_BASE}/browser/sessions/update`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      worker_type: workerType,
      last_login: lastLogin.toISOString(),
    }),
  });
  if (!res.ok) throw new Error("Failed to update browser session");
  return res.json();
}

export async function fetchVNCUrls(): Promise<VNCUrls> {
  const res = await fetch(`${API_BASE}/browser/vnc-urls`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch VNC URLs");
  return res.json();
}

// Session Manager API functions
export interface SessionStatus {
  status: string;
  message?: string;
  archive_path?: string;
  archive_size?: number;
  last_frozen?: string;
}

export async function fetchSessionStatus(): Promise<SessionStatus> {
  const res = await fetch(`${API_BASE}/session/status`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch session status");
  return res.json();
}

export async function freezeSession(): Promise<SessionStatus> {
  const res = await fetch(`${API_BASE}/session/freeze`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to freeze session");
  }
  return res.json();
}

export interface QueueStatus {
  queues: {
    [key: string]: {
      paused: boolean;
      pause_info?: {
        reason: string;
        paused_at: number;
      };
    };
  };
}

export async function fetchQueueStatus(): Promise<QueueStatus> {
  const res = await fetch(`${API_BASE}/admin/queues/status`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch queue status");
  return res.json();
}

export async function resumeQueue(queueName: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/admin/queues/${queueName}/resume`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to resume queue");
  return res.json();
}
