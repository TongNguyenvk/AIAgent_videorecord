export type VideoStatus = 'pending' | 'queued' | 'running' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface Video {
  id: string | number;
  title: string;
  status: VideoStatus;
  duration?: string;
  date: string;
  thumbnail?: string | null;
  video_url?: string;
  jobId?: string;
}

// Cổng 8000 của FastAPI container
const API_BASE = 'http://localhost:8000/api'; 

export async function fetchVideos(): Promise<Video[]> {
  try {
    const res = await fetch(`${API_BASE}/jobs`);
    if (!res.ok) throw new Error('Failed to fetch videos');
    const data = await res.json();
    
    // Map response của FastAPI thành chuẩn UI (data.jobs)
    return data.jobs.map((job: any) => ({
      id: job.job_id,
      title: job.video_name || job.task.slice(0, 35) + '...',
      status: job.status,
      date: new Date(job.created_at).toLocaleString(),
      video_url: job.result?.video_url,
      duration: job.result?.duration_seconds ? `${job.result.duration_seconds}s` : '--'
    }));
  } catch (error) {
    console.error("API Error: Backend offline or CORS issue.", error);
    return [];
  }
}

export async function createVideo(data: { 
  prompt: string; 
  tts_engine: string; 
  tts_voice: string; 
  padding_ms: number;
  enable_tts: boolean;
  enable_review: boolean;
}): Promise<Video> {
  const payload = {
    task: data.prompt,
    job_type: 'web', // Đẩy Job cho web-worker
    config: {
      tts_engine: data.tts_engine,
      tts_voice: data.tts_voice,
      padding_ms: data.padding_ms,
      enable_tts: data.enable_tts,
      enable_review: data.enable_review
    }
  };

  const res = await fetch(`${API_BASE}/queue/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  if (!res.ok) {
    throw new Error('Create job failed');
  }
  
  const result = await res.json();
  return {
    id: result.job_id,
    title: payload.task.slice(0, 35) + '...',
    status: result.status, // Thường sẽ là 'queued'
    date: new Date().toISOString()
  };
}
