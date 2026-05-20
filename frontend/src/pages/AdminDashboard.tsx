import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Video, TrendingUp, Shield } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchAdminStats } from "@/lib/api";

export function AdminDashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: fetchAdminStats,
    refetchInterval: 10000,
  });

  if (isLoading || !stats) {
    return (
      <div className="space-y-8">
        <h1 className="text-4xl font-extrabold">Admin Dashboard</h1>
        <div className="grid gap-6 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card
              key={i}
              className="border shadow-lg dark:border-white/10 dark:bg-white/5 animate-pulse"
            >
              <CardHeader className="pb-2">
                <div className="h-4 bg-muted rounded w-24"></div>
              </CardHeader>
              <CardContent>
                <div className="h-10 bg-muted rounded w-16"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-br from-foreground to-muted-foreground bg-clip-text text-transparent">
          System Overview
        </h1>
        <p className="text-muted-foreground mt-2 text-lg">
          Tổng quan hệ thống và thống kê
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-4">
        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-white/5 dark:backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Tổng người dùng
            </CardTitle>
            <Users className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-gray-900 dark:text-white">
              {stats.users.total}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {stats.users.active} hoạt động, {stats.users.suspended} bị khóa
            </p>
          </CardContent>
        </Card>

        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-white/5 dark:backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Tổng Jobs
            </CardTitle>
            <Video className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-gray-900 dark:text-white">
              {stats.jobs.total}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Tất cả người dùng
            </p>
          </CardContent>
        </Card>

        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-white/5 dark:backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Tier Distribution
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-gray-700 dark:text-gray-300">
              <div className="text-sm">Free: {stats.users.by_tier.free}</div>
              <div className="text-sm">Pro: {stats.users.by_tier.pro}</div>
              <div className="text-sm">Enterprise: {stats.users.by_tier.enterprise}</div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-white/5 dark:backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Admins
            </CardTitle>
            <Shield className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-gray-900 dark:text-white">
              {stats.users.by_role.admin}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {stats.users.by_role.user} regular users
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-white/5 dark:backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">
              Job Status Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(stats.jobs.by_status || {}).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between">
                  <span className="text-sm capitalize text-gray-600 dark:text-gray-400">
                    {status}
                  </span>
                  <span className="text-lg font-bold text-gray-900 dark:text-white">
                    {count as number}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border border-gray-200 shadow-lg bg-white dark:border-white/10 dark:bg-white/5 dark:backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Quick Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Total Users
                </span>
                <span className="text-lg font-bold text-gray-900 dark:text-white">
                  {stats.users.total}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Total Jobs
                </span>
                <span className="text-lg font-bold text-gray-900 dark:text-white">
                  {stats.jobs.total}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Active Rate
                </span>
                <span className="text-lg font-bold text-gray-900 dark:text-white">
                  {((stats.users.active / stats.users.total) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
