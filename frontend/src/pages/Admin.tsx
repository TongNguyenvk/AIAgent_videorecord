import { useQuery } from "@tanstack/react-query";
import {
  fetchAllUsers,
  fetchAllJobs,
  updateUserTier,
  suspendUser,
  activateUser,
  type AdminUser,
} from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users as UsersIcon, Video, Loader2, Ban, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { AdminDashboard } from "./AdminDashboard";

export function Admin() {
  const location = useLocation();
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [selectedTier, setSelectedTier] = useState<string>("");

  // Determine which tab to show based on URL
  const currentPath = location.pathname;
  const showUsers = currentPath === "/admin/users";
  const showJobs = currentPath === "/admin/jobs";
  const showDashboard = currentPath === "/admin" || (!showUsers && !showJobs);

  const {
    data: users,
    isLoading: usersLoading,
    refetch: refetchUsers,
  } = useQuery({
    queryKey: ["admin-users"],
    queryFn: fetchAllUsers,
    refetchInterval: 10000,
    enabled: showUsers,
  });

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["admin-jobs"],
    queryFn: fetchAllJobs,
    refetchInterval: 5000,
    enabled: showJobs,
  });

  const handleSuspendUser = async (user: AdminUser) => {
    if (!confirm(`Bạn có chắc muốn tạm khóa tài khoản ${user.email}?`)) return;

    const reason = prompt("Lý do tạm khóa:");
    if (!reason) return;

    setActionLoading(user.user_id);
    try {
      await suspendUser(user.user_id, reason);
      toast.success("Đã tạm khóa tài khoản");
      refetchUsers();
    } catch (error) {
      toast.error("Lỗi khi tạm khóa tài khoản");
    } finally {
      setActionLoading(null);
    }
  };

  const handleActivateUser = async (user: AdminUser) => {
    setActionLoading(user.user_id);
    try {
      await activateUser(user.user_id);
      toast.success("Đã kích hoạt tài khoản");
      refetchUsers();
    } catch (error) {
      toast.error("Lỗi khi kích hoạt tài khoản");
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpdateTier = async (user: AdminUser) => {
    setEditingUser(user);
    setSelectedTier(user.tier);
  };

  const confirmUpdateTier = async () => {
    if (!editingUser || !selectedTier) return;

    setActionLoading(editingUser.user_id);
    try {
      await updateUserTier(editingUser.user_id, selectedTier);
      toast.success("Đã cập nhật tier");
      refetchUsers();
      setEditingUser(null);
      setSelectedTier("");
    } catch (error) {
      toast.error("Lỗi khi cập nhật tier");
    } finally {
      setActionLoading(null);
    }
  };

  // Show Dashboard tab
  if (showDashboard) {
    return <AdminDashboard />;
  }

  // Show Users tab
  if (showUsers) {
    return (
      <>
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-br from-foreground to-muted-foreground bg-clip-text text-transparent">
              Quản lý người dùng
            </h1>
            <p className="text-muted-foreground mt-2 text-lg">
              Quản lý người dùng và phân quyền
            </p>
          </div>

          <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-black/40 dark:backdrop-blur-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UsersIcon className="w-5 h-5" />
                Tất cả người dùng
              </CardTitle>
            </CardHeader>
            <CardContent>
              {usersLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              ) : (
                <div className="rounded-lg border border-gray-200 dark:border-white/10 overflow-hidden shadow-sm">
                  <Table>
                    <TableHeader className="bg-gray-50/50 dark:bg-white/5 border-b border-gray-200 dark:border-white/10">
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Email
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Tên
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Vai trò
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Gói
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Trạng thái
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Hạn mức
                        </TableHead>
                        <TableHead className="text-right font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Hành động
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="bg-white dark:bg-transparent">
                      {users?.map((user) => (
                        <TableRow
                          key={user.user_id}
                          className="border-b border-gray-100 dark:border-white/5 hover:bg-gray-50/50 dark:hover:bg-white/5 transition-colors bg-white dark:bg-transparent"
                        >
                          <TableCell className="font-medium text-gray-900 dark:text-gray-100">
                            {user.email}
                          </TableCell>
                          <TableCell className="text-gray-700 dark:text-gray-300">
                            {user.name}
                          </TableCell>
                          <TableCell>
                            {user.role === "admin" ? (
                              <Badge
                                variant="outline"
                                className="bg-red-50 text-red-600 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20"
                              >
                                Quản trị viên
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20"
                              >
                                Người dùng
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className="bg-purple-50 text-purple-600 border-purple-200 dark:bg-purple-500/10 dark:text-purple-400 dark:border-purple-500/20"
                            >
                              {user.tier === "free"
                                ? "Miễn phí"
                                : user.tier === "pro"
                                  ? "Chuyên nghiệp"
                                  : "Doanh nghiệp"}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {user.status === "active" ? (
                              <Badge
                                variant="outline"
                                className="bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20"
                              >
                                Hoạt động
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="bg-red-50 text-red-600 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20"
                              >
                                Đã khóa
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {user.quota.videos_used_this_month}/
                            {user.quota.videos_per_month}
                          </TableCell>
                          <TableCell className="text-right space-x-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleUpdateTier(user)}
                              disabled={actionLoading === user.user_id}
                            >
                              Đổi gói
                            </Button>
                            {user.status === "active" ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleSuspendUser(user)}
                                disabled={actionLoading === user.user_id}
                                className="border-red-200 text-red-600 hover:bg-red-50 dark:border-red-500/20 dark:text-red-400 dark:hover:bg-red-500/10"
                              >
                                {actionLoading === user.user_id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <>
                                    <Ban className="w-4 h-4 mr-1" />
                                    Khóa
                                  </>
                                )}
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleActivateUser(user)}
                                disabled={actionLoading === user.user_id}
                                className="border-emerald-200 text-emerald-600 hover:bg-emerald-50 dark:border-emerald-500/20 dark:text-emerald-400 dark:hover:bg-emerald-500/10"
                              >
                                {actionLoading === user.user_id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <>
                                    <CheckCircle className="w-4 h-4 mr-1" />
                                    Kích hoạt
                                  </>
                                )}
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {editingUser && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setEditingUser(null)}
          >
            <Card
              className="w-full max-w-md border border-gray-200 shadow-xl bg-white dark:border-white/10 dark:bg-black/90"
              onClick={(e) => e.stopPropagation()}
            >
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">
                  Cập nhật gói dịch vụ
                </CardTitle>
                <CardDescription>Chọn gói mới cho {editingUser.email}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Gói hiện tại:{" "}
                    <span className="text-primary">
                      {editingUser.tier === "free"
                        ? "Miễn phí"
                        : editingUser.tier === "pro"
                          ? "Chuyên nghiệp"
                          : "Doanh nghiệp"}
                    </span>
                  </label>
                  <select
                    className="flex h-12 w-full items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary text-gray-900 dark:border-white/10 dark:bg-white/5 dark:text-white"
                    value={selectedTier}
                    onChange={(e) => setSelectedTier(e.target.value)}
                  >
                    <option value="" disabled className="bg-white dark:bg-zinc-900">
                      Chọn gói mới
                    </option>
                    <option value="free" className="bg-white dark:bg-zinc-900">
                      Miễn phí (100 video/tháng)
                    </option>
                    <option value="pro" className="bg-white dark:bg-zinc-900">
                      Chuyên nghiệp (500 video/tháng)
                    </option>
                    <option value="enterprise" className="bg-white dark:bg-zinc-900">
                      Doanh nghiệp (Không giới hạn)
                    </option>
                  </select>
                </div>
                <div className="flex gap-3 justify-end">
                  <Button variant="outline" onClick={() => setEditingUser(null)}>
                    Hủy
                  </Button>
                  <Button
                    onClick={confirmUpdateTier}
                    disabled={
                      !selectedTier ||
                      selectedTier === editingUser.tier ||
                      actionLoading === editingUser.user_id
                    }
                  >
                    {actionLoading === editingUser.user_id ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Đang cập nhật...
                      </>
                    ) : (
                      "Cập nhật"
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </>
    );
  }

  // Show Jobs tab
  if (showJobs) {
    return (
      <>
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-br from-foreground to-muted-foreground bg-clip-text text-transparent">
              Tất cả công việc
            </h1>
            <p className="text-muted-foreground mt-2 text-lg">
              Tất cả jobs của mọi người dùng
            </p>
          </div>

          <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-black/40 dark:backdrop-blur-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Video className="w-5 h-5" />
                Danh sách công việc
              </CardTitle>
            </CardHeader>
            <CardContent>
              {jobsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              ) : (
                <div className="rounded-lg border border-gray-200 dark:border-white/10 overflow-hidden shadow-sm">
                  <Table>
                    <TableHeader className="bg-gray-50/50 dark:bg-white/5 border-b border-gray-200 dark:border-white/10">
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Mã công việc
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Tiêu đề
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Mã người dùng
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Trạng thái
                        </TableHead>
                        <TableHead className="font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Ngày tạo
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="bg-white dark:bg-transparent">
                      {jobs?.slice(0, 50).map((job) => (
                        <TableRow
                          key={job.id}
                          className="border-b border-gray-100 dark:border-white/5 hover:bg-gray-50/50 dark:hover:bg-white/5 transition-colors bg-white dark:bg-transparent"
                        >
                          <TableCell className="font-mono text-xs text-gray-600 dark:text-gray-400">
                            {String(job.id).slice(0, 8)}...
                          </TableCell>
                          <TableCell className="text-gray-900 dark:text-gray-100">
                            {job.title}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-gray-500 dark:text-muted-foreground">
                            {(job as any).user_id?.slice(0, 8) || "N/A"}...
                          </TableCell>
                          <TableCell>
                            {job.status === "completed" && (
                              <Badge
                                variant="outline"
                                className="bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20"
                              >
                                Hoàn thành
                              </Badge>
                            )}
                            {["pending", "queued", "running", "processing"].includes(
                              job.status,
                            ) && (
                              <Badge
                                variant="outline"
                                className="bg-yellow-50 text-yellow-600 border-yellow-200 dark:bg-yellow-500/10 dark:text-yellow-400 dark:border-yellow-500/20"
                              >
                                Đang xử lý
                              </Badge>
                            )}
                            {["failed", "cancelled"].includes(job.status) && (
                              <Badge
                                variant="outline"
                                className="bg-red-50 text-red-600 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20"
                              >
                                {job.status === "failed" ? "Thất bại" : "Đã hủy"}
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {job.date}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {editingUser && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setEditingUser(null)}
          >
            <Card
              className="w-full max-w-md border border-gray-200 shadow-xl bg-white dark:border-white/10 dark:bg-black/90"
              onClick={(e) => e.stopPropagation()}
            >
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">
                  Cập nhật gói dịch vụ
                </CardTitle>
                <CardDescription>Chọn gói mới cho {editingUser.email}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Gói hiện tại:{" "}
                    <span className="text-primary">
                      {editingUser.tier === "free"
                        ? "Miễn phí"
                        : editingUser.tier === "pro"
                          ? "Chuyên nghiệp"
                          : "Doanh nghiệp"}
                    </span>
                  </label>
                  <select
                    className="flex h-12 w-full items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary text-gray-900 dark:border-white/10 dark:bg-white/5 dark:text-white"
                    value={selectedTier}
                    onChange={(e) => setSelectedTier(e.target.value)}
                  >
                    <option value="" disabled className="bg-white dark:bg-zinc-900">
                      Chọn gói mới
                    </option>
                    <option value="free" className="bg-white dark:bg-zinc-900">
                      Miễn phí (100 video/tháng)
                    </option>
                    <option value="pro" className="bg-white dark:bg-zinc-900">
                      Chuyên nghiệp (500 video/tháng)
                    </option>
                    <option value="enterprise" className="bg-white dark:bg-zinc-900">
                      Doanh nghiệp (Không giới hạn)
                    </option>
                  </select>
                </div>
                <div className="flex gap-3 justify-end">
                  <Button variant="outline" onClick={() => setEditingUser(null)}>
                    Hủy
                  </Button>
                  <Button
                    onClick={confirmUpdateTier}
                    disabled={
                      !selectedTier ||
                      selectedTier === editingUser.tier ||
                      actionLoading === editingUser.user_id
                    }
                  >
                    {actionLoading === editingUser.user_id ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Đang cập nhật...
                      </>
                    ) : (
                      "Cập nhật"
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </>
    );
  }

  return null;
}
