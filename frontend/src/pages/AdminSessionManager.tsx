import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchSessionStatus,
  fetchVNCUrls,
  freezeSession,
  fetchQueueStatus,
  resumeQueue,
} from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Monitor,
  Snowflake,
  RefreshCw,
  Loader2,
  Server,
  Clock,
  HardDrive,
  ShieldAlert,
  Play,
  PauseCircle,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

const NOVNC_URL =
  import.meta.env.VITE_NOVNC_URL ||
  "/novnc/vnc.html?autoconnect=true&resize=scale&path=websockify";

// Tên hiển thị thân thiện cho từng queue
const QUEUE_LABELS: Record<string, string> = {
  "web-queue": "Web hướng dẫn",
  "presentation-queue": "Trình chiếu OneDrive",
  "presentation-gg-queue": "Trình chiếu Google",
  "office-queue": "Office",
};

export function AdminSessionManager() {
  const queryClient = useQueryClient();

  // Session Manager status
  const {
    data: sessionStatus,
    isLoading: statusLoading,
    refetch: refetchStatus,
  } = useQuery({
    queryKey: ["session-status"],
    queryFn: fetchSessionStatus,
    refetchInterval: 30000,
  });

  const {
    data: vncUrls,
    isLoading: vncUrlsLoading,
    refetch: refetchVncUrls,
  } = useQuery({
    queryKey: ["vnc-urls"],
    queryFn: fetchVNCUrls,
    staleTime: 0,
    refetchOnMount: "always",
  });

  // Circuit Breaker: Queue pause status
  const {
    data: queueStatus,
    isLoading: queueLoading,
    refetch: refetchQueues,
  } = useQuery({
    queryKey: ["queue-status"],
    queryFn: fetchQueueStatus,
    refetchInterval: 10000,
  });

  const freezeMutation = useMutation({
    mutationFn: freezeSession,
    onSuccess: () => {
      toast.success("Đã lưu và đóng băng phiên");
      refetchStatus();
    },
    onError: (error: Error) => {
      toast.error(`Không thể lưu phiên: ${error.message}`);
    },
  });

  const resumeMutation = useMutation({
    mutationFn: (queueName: string) => resumeQueue(queueName),
    onSuccess: (_data, queueName) => {
      toast.success(`Đã mở lại "${QUEUE_LABELS[queueName] || queueName}"`);
      queryClient.invalidateQueries({ queryKey: ["queue-status"] });
    },
    onError: (error: Error) => {
      toast.error(`Không thể mở lại hàng đợi: ${error.message}`);
    },
  });

  const lastFrozenTime = sessionStatus?.last_frozen
    ? new Date(sessionStatus.last_frozen).toLocaleString("vi-VN")
    : null;
  const novncUrl = vncUrls?.web?.url || NOVNC_URL;

  // Kiểm tra có queue nào đang bị pause không
  const pausedQueues = queueStatus?.queues
    ? Object.entries(queueStatus.queues).filter(([, info]) => info.paused)
    : [];
  const hasPausedQueues = pausedQueues.length > 0;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ready":
        return <Badge className="bg-emerald-500">Sẵn sàng</Badge>;
      case "frozen":
        return <Badge className="bg-blue-500">Đã lưu phiên</Badge>;
      case "unavailable":
        return <Badge className="bg-red-500">Không khả dụng</Badge>;
      default:
        return <Badge variant="outline">{status || "Không rõ"}</Badge>;
    }
  };

  const formatPauseTime = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString("vi-VN");
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-br from-foreground to-muted-foreground bg-clip-text text-transparent">
          Quản lý phiên đăng nhập
        </h1>
        <p className="text-muted-foreground mt-2 text-lg">
          Đăng nhập Microsoft hoặc Google tại đây, sau đó lưu phiên để worker dùng.
        </p>
      </div>

      {hasPausedQueues && (
        <Card className="border-2 border-red-500 shadow-lg shadow-red-500/10 bg-red-50 dark:bg-red-950/30 dark:border-red-500/60 animate-in fade-in slide-in-from-top-2 duration-500">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-red-700 dark:text-red-400">
              <ShieldAlert className="w-5 h-5" />
              Hàng đợi đã tạm dừng do phiên hết hạn
            </CardTitle>
            <CardDescription className="text-red-600 dark:text-red-400/80">
              Một hoặc nhiều hàng đợi đang dừng để tránh job lỗi lặp lại. Hãy đăng
              nhập lại trong trình duyệt bên dưới, lưu phiên, rồi mở lại hàng đợi.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pausedQueues.map(([queueName, info]) => (
                <div
                  key={queueName}
                  className="flex items-center justify-between p-3 bg-white dark:bg-black/40 rounded-lg border border-red-200 dark:border-red-500/20"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <PauseCircle className="w-4 h-4 text-red-500" />
                      <span className="font-semibold text-sm">
                        {QUEUE_LABELS[queueName] || queueName}
                      </span>
                      <Badge className="bg-red-500 text-xs">Đã tạm dừng</Badge>
                    </div>
                    {info.pause_info && (
                      <div className="text-xs text-muted-foreground mt-1 ml-6">
                        <span>Lý do: {info.pause_info.reason}</span>
                        {info.pause_info.paused_at && (
                          <span className="ml-3">
                            Từ: {formatPauseTime(info.pause_info.paused_at)}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-emerald-500 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                    onClick={() => resumeMutation.mutate(queueName)}
                    disabled={resumeMutation.isPending}
                  >
                    {resumeMutation.isPending ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 mr-1" />
                    )}
                    Mở lại
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-4">
        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-black/40 dark:backdrop-blur-2xl">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Server className="w-4 h-4" />
              Trạng thái phiên
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statusLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              getStatusBadge(sessionStatus?.status || "unavailable")
            )}
            {sessionStatus?.message && (
              <p className="text-xs text-muted-foreground mt-2">
                {sessionStatus.message}
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-black/40 dark:backdrop-blur-2xl">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Clock className="w-4 h-4" />
              Lần lưu gần nhất
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lastFrozenTime ? (
              <span className="text-lg font-semibold">{lastFrozenTime}</span>
            ) : (
              <span className="text-muted-foreground">Chưa lưu</span>
            )}
          </CardContent>
        </Card>

        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-black/40 dark:backdrop-blur-2xl">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <HardDrive className="w-4 h-4" />
              Dung lượng phiên
            </CardTitle>
          </CardHeader>
          <CardContent>
            {sessionStatus?.archive_size ? (
              <span className="text-lg font-semibold">
                {(sessionStatus.archive_size / 1024 / 1024).toFixed(2)} MB
              </span>
            ) : (
              <span className="text-muted-foreground">-</span>
            )}
          </CardContent>
        </Card>

        <Card
          className={`border shadow-lg bg-white dark:bg-black/40 dark:backdrop-blur-2xl ${
            hasPausedQueues
              ? "border-red-300 dark:border-red-500/30"
              : "border-gray-200 dark:border-white/10"
          }`}
        >
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <ShieldAlert className="w-4 h-4" />
              Bảo vệ hàng đợi
            </CardTitle>
          </CardHeader>
          <CardContent>
            {queueLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : hasPausedQueues ? (
              <div className="flex items-center gap-2">
                <Badge className="bg-red-500">
                  {pausedQueues.length} hàng đợi tạm dừng
                </Badge>
                <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" />
              </div>
            ) : (
              <Badge className="bg-emerald-500">Tất cả đang chạy</Badge>
            )}
          </CardContent>
        </Card>
      </div>

      {queueStatus?.queues && (
        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-black/40 dark:backdrop-blur-2xl">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldAlert className="w-5 h-5" />
                  Trạng thái hàng đợi
                </CardTitle>
                <CardDescription className="mt-1">
                  Khi phiên đăng nhập hết hạn, hệ thống tự tạm dừng hàng đợi liên quan.
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetchQueues()}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Làm mới
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {Object.entries(queueStatus.queues).map(([queueName, info]) => (
                <div
                  key={queueName}
                  className={`flex items-center justify-between p-4 rounded-lg border ${
                    info.paused
                      ? "bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-500/20"
                      : "bg-gray-50 border-gray-200 dark:bg-white/5 dark:border-white/10"
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      {info.paused ? (
                        <PauseCircle className="w-4 h-4 text-red-500" />
                      ) : (
                        <Play className="w-4 h-4 text-emerald-500" />
                      )}
                      <span className="font-medium text-sm">
                        {QUEUE_LABELS[queueName] || queueName}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground ml-6">
                      {info.paused ? "Đã tạm dừng" : "Đang chạy"}
                    </span>
                  </div>
                  {info.paused && (
                    <Button
                      size="sm"
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      onClick={() => resumeMutation.mutate(queueName)}
                      disabled={resumeMutation.isPending}
                    >
                      {resumeMutation.isPending ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <Play className="w-4 h-4 mr-1" />
                      )}
                      Mở lại
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-black/40 dark:backdrop-blur-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Snowflake className="w-5 h-5" />
            Lưu phiên cho worker
          </CardTitle>
          <CardDescription>
            Đóng Chrome an toàn và lưu lại profile để worker dùng cho các job mới.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-white/5 rounded-lg">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Hãy đảm bảo đã đăng nhập các nền tảng cần thiết trong trình duyệt bên dưới
              trước khi lưu phiên.
            </div>
            <Button
              onClick={() => freezeMutation.mutate()}
              disabled={freezeMutation.isPending}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {freezeMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Đang lưu...
                </>
              ) : (
                <>
                  <Snowflake className="w-4 h-4 mr-2" />
                  Lưu phiên
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-black/40 dark:backdrop-blur-2xl">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="w-5 h-5" />
                Trình duyệt từ xa
              </CardTitle>
              <CardDescription className="mt-2">
                Dùng noVNC để đăng nhập Microsoft hoặc Google. Sau khi đăng nhập xong,
                bấm "Lưu phiên" ở phía trên.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetchStatus();
                refetchVncUrls();
              }}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Làm mới
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20 rounded-lg p-4">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                Đăng nhập các nền tảng cần dùng như Microsoft 365 hoặc Google trong trình
                duyệt này. Khi xong, bấm "Lưu phiên" để worker sử dụng.
              </p>
            </div>

            <div className="border border-gray-200 dark:border-white/10 rounded-lg overflow-hidden bg-black">
              {vncUrlsLoading && !vncUrls ? (
                <div className="w-full h-[600px] flex items-center justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-white" />
                </div>
              ) : (
                <iframe
                  key={novncUrl}
                  src={novncUrl}
                  className="w-full h-[600px]"
                  title="noVNC - Quản lý phiên"
                  allow="clipboard-read; clipboard-write"
                />
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
