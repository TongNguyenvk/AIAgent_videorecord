import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Loader2, PlayCircle, Save, X, Edit2 } from "lucide-react";
import { getJobScript, approveScript } from "@/lib/api";
import { toast } from "sonner";

interface Segment {
  id: string;
  text: string;
  timing?: number;
  action_type?: string;
  edited?: boolean;
  approved?: boolean;
}

interface ScriptData {
  segments: Segment[];
  total_segments: number;
  reviewed_segments: number;
  approved_segments: number;
  review_status: string;
}

interface Phase25ReviewProps {
  jobId: string;
  onApprove: () => void;
  onClose: () => void;
}

export function Phase25Review({ jobId, onApprove, onClose }: Phase25ReviewProps) {
  const [script, setScript] = useState<ScriptData | null>(null);
  const [editedSegments, setEditedSegments] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    loadScript();
  }, [jobId]);

  const loadScript = async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const scriptData = await getJobScript(jobId);

      if (Array.isArray(scriptData)) {
        setScript({
          segments: scriptData.map((seg: any, i: number) => ({
            id: seg.id || `seg_${String(i).padStart(3, "0")}`,
            text: seg.narration || seg.text || "",
            timing: seg.duration || seg.timing,
            action_type: seg.action_type || "",
          })),
          total_segments: scriptData.length,
          reviewed_segments: 0,
          approved_segments: 0,
          review_status: "pending",
        });
      } else if (scriptData && scriptData.segments) {
        setScript(scriptData);
      } else {
        setLoadError("Kịch bản chưa sẵn sàng. Worker có thể chưa chạy xong Phase 2.");
      }
    } catch (error) {
      setLoadError("Không thể tải kịch bản. Kiểm tra kết nối backend.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSegmentEdit = (segmentId: string, newText: string) => {
    setEditedSegments((prev) => ({
      ...prev,
      [segmentId]: newText,
    }));
  };

  const handleApprove = async () => {
    if (!script) return;

    try {
      setApproving(true);

      const ttsScript = script.segments.map((segment) => ({
        ...segment,
        text: editedSegments[segment.id] ?? segment.text,
        narration: editedSegments[segment.id] ?? segment.text,
        edited: !!editedSegments[segment.id],
        approved: true,
      }));

      await approveScript(jobId, ttsScript);
      toast.success("Đã duyệt kịch bản", {
        description: "Job sẽ tiếp tục chạy Phase 3 (TTS).",
      });
      onApprove();
    } catch (error) {
      toast.error("Lỗi khi duyệt", {
        description: "Không thể gửi phê duyệt lên server.",
      });
      console.error(error);
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="bg-white dark:bg-zinc-950 border border-gray-200 dark:border-white/10 p-8 rounded-xl flex flex-col items-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
          <p className="text-gray-700 dark:text-zinc-300">
            {"Đang tải kịch bản Phase 2.5..."}
          </p>
        </div>
      </div>
    );
  }

  if (loadError || !script) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="bg-white dark:bg-zinc-950 border border-gray-200 dark:border-white/10 p-8 rounded-xl max-w-md w-full">
          <h2 className="text-xl font-bold text-red-600 dark:text-red-400 mb-2">
            {"Không tải được kịch bản"}
          </h2>
          <p className="text-gray-600 dark:text-zinc-400 mb-6">
            {loadError || "Kịch bản chưa sẵn sàng hoặc đã xảy ra lỗi."}
          </p>
          <div className="flex justify-between">
            <Button onClick={loadScript} variant="secondary">
              {"Thử lại"}
            </Button>
            <Button
              onClick={onClose}
              variant="ghost"
              className="text-gray-500 dark:text-zinc-400"
            >
              {"Đóng"}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 sm:p-6">
      <div className="bg-white dark:bg-zinc-950 border border-gray-200 dark:border-white/10 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              {"Review kịch bản TTS (Phase 2.5)"}
            </h2>
            <p className="text-sm text-gray-500 dark:text-zinc-400 mt-1">
              Job ID:{" "}
              <span className="font-mono text-gray-700 dark:text-zinc-300">
                {jobId.substring(0, 8)}...
              </span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 dark:hover:bg-white/10 rounded-full transition-colors text-gray-400 hover:text-gray-900 dark:hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-yellow-500/10 border-b border-yellow-500/20 px-6 py-3 flex items-center gap-3">
          <p className="text-sm text-yellow-800 dark:text-yellow-200/90 font-medium">
            {
              "Vui lòng kiểm tra và sửa lỗi chính tả/ngữ pháp trước khi hệ thống sinh audio (TTS) để tiết kiệm chi phí."
            }
          </p>
        </div>

        <div className="px-6 py-3 flex gap-6 text-sm text-gray-600 dark:text-zinc-400 border-b border-gray-200 dark:border-white/5">
          <span>
            {"Tổng số đoạn: "}
            <strong className="text-gray-900 dark:text-white">
              {script.segments?.length || 0}
            </strong>
          </span>
          <span>
            {"Đã chỉnh sửa: "}
            <strong className="text-primary">{Object.keys(editedSegments).length}</strong>
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar bg-gray-50 dark:bg-transparent">
          {!script.segments || script.segments.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-zinc-500 py-12">
              {"Kịch bản trống"}
            </div>
          ) : (
            script.segments.map((segment, index) => (
              <SegmentEditor
                key={segment.id}
                segment={segment}
                index={index}
                onEdit={(newText) => handleSegmentEdit(segment.id, newText)}
                editedText={editedSegments[segment.id]}
              />
            ))
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 flex items-center justify-between">
          <Button
            variant="ghost"
            className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-500/10"
            onClick={onClose}
          >
            {"Hủy và đóng"}
          </Button>
          <Button
            className="rounded-full px-8 shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all bg-primary hover:bg-primary/90 text-white"
            onClick={handleApprove}
            disabled={approving || !script.segments || script.segments.length === 0}
          >
            {approving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" /> {"Đang duyệt..."}
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" /> {"Duyệt và tiếp tục TTS"}
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

function SegmentEditor({
  segment,
  index,
  onEdit,
  editedText,
}: {
  segment: Segment;
  index: number;
  onEdit: (text: string) => void;
  editedText?: string;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [text, setText] = useState(editedText ?? segment.text);

  const handleSave = () => {
    onEdit(text);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setText(editedText ?? segment.text);
    setIsEditing(false);
  };

  const currentText = editedText ?? segment.text;
  const hasEdits = editedText !== undefined && editedText !== segment.text;

  return (
    <div
      className={`p-4 rounded-xl border transition-all duration-200 ${
        isEditing
          ? "border-primary/50 bg-primary/5"
          : hasEdits
            ? "border-emerald-500/30 bg-emerald-500/5"
            : "border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 hover:border-gray-300 dark:hover:border-white/20"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="bg-gray-200 dark:bg-white/10 text-xs font-mono px-2 py-1 rounded text-gray-700 dark:text-zinc-300">
            #{String(index + 1).padStart(2, "0")}
          </span>
          {segment.timing !== undefined && (
            <span className="text-xs text-gray-500 dark:text-zinc-500 flex items-center gap-1">
              <ClockIcon className="w-3 h-3" /> {segment.timing}s
            </span>
          )}
          {hasEdits && !isEditing && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium bg-emerald-500/10 px-2 py-0.5 rounded">
              {"Đã sửa"}
            </span>
          )}
        </div>

        <div className="flex gap-2">
          {!isEditing && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2 text-gray-600 dark:text-zinc-400 hover:text-gray-900 dark:hover:text-white"
              onClick={() => setIsEditing(true)}
            >
              <Edit2 className="w-4 h-4 mr-1" /> {"Sửa"}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-gray-600 dark:text-zinc-400 hover:text-primary"
          >
            <PlayCircle className="w-4 h-4 mr-1" /> {"Nghe thử"}
          </Button>
        </div>
      </div>

      {isEditing ? (
        <div className="space-y-3 animate-in fade-in slide-in-from-top-1">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="w-full bg-gray-50 dark:bg-black/50 border border-gray-300 dark:border-white/20 rounded-lg p-3 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary min-h-[80px] resize-y custom-scrollbar"
            autoFocus
          />
          <div className="flex items-center justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCancel}
              className="text-gray-600 dark:text-zinc-400"
            >
              {"Hủy"}
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              className="bg-primary text-white hover:bg-primary/90 shadow-md"
            >
              <Save className="w-4 h-4 mr-1" /> {"Lưu"}
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-800 dark:text-zinc-200 leading-relaxed whitespace-pre-wrap">
          {currentText}
        </p>
      )}
    </div>
  );
}

function ClockIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}
