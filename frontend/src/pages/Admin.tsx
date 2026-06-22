import { useQuery } from "@tanstack/react-query";
import {
  fetchAllUsers,
  fetchAllJobs,
  updateUserTier,
  suspendUser,
  activateUser,
  createAdminUser,
  cancelAdminJob,
  type AdminUser,
  type AdminCreateUserPayload,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Users as UsersIcon,
  Video,
  Loader2,
  Ban,
  CheckCircle,
  UserPlus,
  Square,
} from "lucide-react";
import { toast } from "sonner";
import { type FormEvent, useState } from "react";
import { useLocation } from "react-router-dom";
import { AdminDashboard } from "./AdminDashboard";

export function Admin() {
  const location = useLocation();
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [selectedTier, setSelectedTier] = useState<string>("");
  const [creatingUser, setCreatingUser] = useState(false);
  const [newUser, setNewUser] = useState<AdminCreateUserPayload>({
    email: "",
    name: "",
    password: "",
    role: "user",
    tier: "free",
    videos_per_month: 100,
  });
  const [jobToCancel, setJobToCancel] = useState<{
    jobId: string;
    title: string;
  } | null>(null);
  const [cancelReason, setCancelReason] = useState("policy_violation");

  const cancelReasons = [
    { value: "policy_violation", label: "Nội dung vi phạm" },
    { value: "misuse", label: "Dùng sai mục đích" },
    { value: "invalid_material", label: "Tài liệu không hợp lệ" },
    { value: "other", label: "Khác" },
  ];

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

  const {
    data: jobs,
    isLoading: jobsLoading,
    refetch: refetchJobs,
  } = useQuery({
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

  const handleCreateUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setActionLoading("create-user");
    try {
      await createAdminUser({
        ...newUser,
        email: newUser.email.trim(),
        name: newUser.name.trim(),
        videos_per_month: Number(newUser.videos_per_month),
      });
      toast.success("Đã tạo người dùng");
      refetchUsers();
      setCreatingUser(false);
      setNewUser({
        email: "",
        name: "",
        password: "",
        role: "user",
        tier: "free",
        videos_per_month: 100,
      });
    } catch (error) {
      toast.error((error as Error).message || "Lỗi khi tạo người dùng");
    } finally {
      setActionLoading(null);
    }
  };

  const confirmCancelJob = async () => {
    if (!jobToCancel) return;

    setActionLoading(jobToCancel.jobId);
    try {
      const result = await cancelAdminJob(jobToCancel.jobId, cancelReason);
      toast.success(`Đã dừng job: ${result.reason_label}`);
      refetchJobs();
      setJobToCancel(null);
      setCancelReason("policy_violation");
    } catch (error) {
      toast.error((error as Error).message || "Lỗi khi dừng job");
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
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-br from-foreground to-muted-foreground bg-clip-text text-transparent">
                Quản lý người dùng
              </h1>
              <p className="text-muted-foreground mt-2 text-lg">
                Quản lý người dùng, phân quyền và hạn mức tạo job
              </p>
            </div>
            <Button onClick={() => setCreatingUser(true)}>
              <UserPlus className="w-4 h-4 mr-2" />
              Tạo người dùng
            </Button>
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

        {creatingUser && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setCreatingUser(false)}
          >
            <Card
              className="w-full max-w-lg border border-gray-200 shadow-xl bg-white dark:border-white/10 dark:bg-black/90"
              onClick={(e) => e.stopPropagation()}
            >
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">
                  Tạo người dùng mới
                </CardTitle>
                <CardDescription>
                  Tài khoản được kích hoạt ngay, không cần xác thực email.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form className="space-y-4" onSubmit={handleCreateUser}>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="new-user-name">Tên</Label>
                      <Input
                        id="new-user-name"
                        value={newUser.name}
                        onChange={(e) =>
                          setNewUser((prev) => ({ ...prev, name: e.target.value }))
                        }
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="new-user-email">Email</Label>
                      <Input
                        id="new-user-email"
                        type="email"
                        value={newUser.email}
                        onChange={(e) =>
                          setNewUser((prev) => ({ ...prev, email: e.target.value }))
                        }
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="new-user-password">Mật khẩu</Label>
                    <Input
                      id="new-user-password"
                      type="password"
                      value={newUser.password}
                      onChange={(e) =>
                        setNewUser((prev) => ({ ...prev, password: e.target.value }))
                      }
                      minLength={8}
                      required
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="space-y-2">
                      <Label htmlFor="new-user-role">Vai trò</Label>
                      <select
                        id="new-user-role"
                        className="flex h-10 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary text-gray-900 dark:border-white/10 dark:bg-white/5 dark:text-white"
                        value={newUser.role}
                        onChange={(e) =>
                          setNewUser((prev) => ({
                            ...prev,
                            role: e.target.value as "user" | "admin",
                          }))
                        }
                      >
                        <option value="user" className="bg-white dark:bg-zinc-900">
                          Người dùng
                        </option>
                        <option value="admin" className="bg-white dark:bg-zinc-900">
                          Quản trị viên
                        </option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="new-user-tier">Gói</Label>
                      <select
                        id="new-user-tier"
                        className="flex h-10 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary text-gray-900 dark:border-white/10 dark:bg-white/5 dark:text-white"
                        value={newUser.tier}
                        onChange={(e) =>
                          setNewUser((prev) => ({ ...prev, tier: e.target.value }))
                        }
                      >
                        <option value="free" className="bg-white dark:bg-zinc-900">
                          Miễn phí
                        </option>
                        <option value="pro" className="bg-white dark:bg-zinc-900">
                          Chuyên nghiệp
                        </option>
                        <option value="enterprise" className="bg-white dark:bg-zinc-900">
                          Doanh nghiệp
                        </option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="new-user-quota">Job/tháng</Label>
                      <Input
                        id="new-user-quota"
                        type="number"
                        min={0}
                        value={newUser.videos_per_month}
                        onChange={(e) =>
                          setNewUser((prev) => ({
                            ...prev,
                            videos_per_month: Number(e.target.value),
                          }))
                        }
                        required
                      />
                    </div>
                  </div>

                  <div className="flex gap-3 justify-end pt-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setCreatingUser(false)}
                    >
                      Hủy
                    </Button>
                    <Button type="submit" disabled={actionLoading === "create-user"}>
                      {actionLoading === "create-user" ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Đang tạo...
                        </>
                      ) : (
                        "Tạo tài khoản"
                      )}
                    </Button>
                  </div>
                </form>
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
                        <TableHead className="text-right font-semibold text-gray-700 dark:text-gray-300 bg-transparent">
                          Hành động
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
                            {job.status === "cancelled" && job.cancel_message && (
                              <span className="block text-xs text-red-600 dark:text-red-300 mt-1">
                                {job.cancel_message}
                              </span>
                            )}
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
                            {job.status === "pending_review" && (
                              <Badge
                                variant="outline"
                                className="bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20"
                              >
                                Chờ duyệt
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
                          <TableCell className="text-right">
                            {job.status === "running" ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  setJobToCancel({
                                    jobId: String(job.id),
                                    title: job.title,
                                  })
                                }
                                disabled={actionLoading === String(job.id)}
                                className="border-red-200 text-red-600 hover:bg-red-50 dark:border-red-500/20 dark:text-red-400 dark:hover:bg-red-500/10"
                              >
                                {actionLoading === String(job.id) ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <>
                                    <Square className="w-4 h-4 mr-1" />
                                    Dừng
                                  </>
                                )}
                              </Button>
                            ) : (
                              <span className="text-xs text-muted-foreground">-</span>
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

        {jobToCancel && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setJobToCancel(null)}
          >
            <Card
              className="w-full max-w-md border border-gray-200 shadow-xl bg-white dark:border-white/10 dark:bg-black/90"
              onClick={(e) => e.stopPropagation()}
            >
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">
                  Dừng job đang chạy
                </CardTitle>
                <CardDescription>
                  Job sẽ chuyển sang trạng thái đã hủy và worker đang chạy sẽ được dừng.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Job</Label>
                  <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 dark:border-white/10 dark:bg-white/5 dark:text-gray-300">
                    <div className="font-medium">{jobToCancel.title}</div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {jobToCancel.jobId}
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="admin-job-cancel-reason">Lý do</Label>
                  <select
                    id="admin-job-cancel-reason"
                    className="flex h-10 w-full items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary text-gray-900 dark:border-white/10 dark:bg-white/5 dark:text-white"
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                  >
                    {cancelReasons.map((reason) => (
                      <option
                        key={reason.value}
                        value={reason.value}
                        className="bg-white dark:bg-zinc-900"
                      >
                        {reason.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-3 justify-end">
                  <Button variant="outline" onClick={() => setJobToCancel(null)}>
                    Hủy
                  </Button>
                  <Button
                    onClick={confirmCancelJob}
                    disabled={actionLoading === jobToCancel.jobId}
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    {actionLoading === jobToCancel.jobId ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Đang dừng...
                      </>
                    ) : (
                      "Dừng job"
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
