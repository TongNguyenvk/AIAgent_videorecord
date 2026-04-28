import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { PlayCircle, Plus, LayoutGrid, Clock, CheckCircle2, AlertCircle, Loader2, RefreshCcw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchVideos } from '@/lib/api'

export function Dashboard() {
  const { data: videos, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['videos'],
    queryFn: fetchVideos,
    refetchInterval: 5000, // Tự động Polling mỗi 5 giây
  })

  // Gọi trực tiếp từ Hook (đã có handler mock fallback bên trong api.ts)
  const displayVideos = videos || [];
  
  const totalCompleted = displayVideos.filter(v => v.status === 'completed').length;
  const successRate = displayVideos.length > 0 ? ((totalCompleted / displayVideos.length) * 100).toFixed(1) : '100.0';
  const totalProcessing = displayVideos.filter(v => ['pending', 'queued', 'running', 'processing'].includes(v.status)).length;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-br from-white to-zinc-500 bg-clip-text text-transparent">Overview</h1>
          <p className="text-muted-foreground mt-2 text-lg">Hệ thống quản trị và giám sát trạng thái render video.</p>
        </div>
        <div className="flex items-center gap-3">
          {isFetching && <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />}
          <Link to="/create" className={buttonVariants({ size: "lg", className: "rounded-full shadow-lg shadow-primary/20 transition-all hover:scale-105 active:scale-95" })}>
            <Plus className="mr-2 h-5 w-5" />
            Tạo Video Mới
          </Link>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="bg-white/5 border-white/10 backdrop-blur-xl shadow-2xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Tổng Video</CardTitle>
            <LayoutGrid className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{displayVideos.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Giao dịch trong tháng này</p>
          </CardContent>
        </Card>
        
        <Card className="bg-white/5 border-white/10 backdrop-blur-xl shadow-2xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Đang xử lý</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{totalProcessing}</div>
            <p className="text-xs text-muted-foreground mt-1">Sẽ hoàn thành trong ~5 phút</p>
          </CardContent>
        </Card>
        
        <Card className="bg-white/5 border-white/10 backdrop-blur-xl shadow-2xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Tỷ lệ thành công</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{successRate}%</div>
            <p className="text-xs text-muted-foreground mt-1">Thống kê toàn thời gian</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-white/10 bg-black/40 backdrop-blur-2xl shadow-xl overflow-hidden rounded-2xl">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white">Video gần đây</h2>
            <Button variant="outline" size="sm" onClick={() => refetch()} className="border-white/10 hover:bg-white/10">
               <RefreshCcw className="w-4 h-4 mr-2" />
               Làm mới
            </Button>
          </div>
          
          <div className="rounded-md border border-white/10 bg-background/50">
            <Table>
              <TableHeader className="bg-white/5 hover:bg-white/5">
                <TableRow className="border-white/10 text-muted-foreground hover:bg-transparent">
                  <TableHead className="w-[80px]">Media</TableHead>
                  <TableHead>Tiêu đề</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Thời lượng</TableHead>
                  <TableHead className="text-right">Hành động</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                     <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                        Đang lấy dữ liệu từ API...
                     </TableCell>
                  </TableRow>
                ) : displayVideos.map((video) => (
                  <TableRow key={video.id} className="border-white/5 hover:bg-white/5 transition-colors group">
                    <TableCell>
                      <div className="h-12 w-20 rounded bg-zinc-800/80 overflow-hidden relative border border-white/10 group-hover:border-primary/50 transition-colors flex items-center justify-center">
                        {video.thumbnail ? (
                          <>
                            <img src={video.thumbnail} alt={video.title} className="w-full h-full object-cover opacity-80" />
                            <PlayCircle className="absolute w-6 h-6 text-white drop-shadow-md opacity-0 group-hover:opacity-100 transition-opacity" />
                          </>
                        ) : (
                          <div className="flex items-center justify-center w-full h-full text-zinc-600">
                             {['pending', 'queued', 'running', 'processing'].includes(video.status) ? <Clock className="w-5 h-5 animate-pulse text-yellow-500/70" /> : <AlertCircle className="w-5 h-5 text-red-500/70" />}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-medium text-base text-zinc-200">
                      {video.title}
                      <span className="block text-xs text-muted-foreground mt-1 font-normal opacity-70">{video.date}</span>
                    </TableCell>
                    <TableCell>
                      {video.status === 'completed' && <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 px-3 py-1 font-medium">Hoàn thành</Badge>}
                      {['pending', 'queued', 'running', 'processing'].includes(video.status) && <Badge variant="outline" className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20 px-3 py-1 font-medium animate-pulse">Đang xử lý</Badge>}
                      {['failed', 'cancelled'].includes(video.status) && <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/20 px-3 py-1 font-medium">Thất bại / Hủy</Badge>}
                    </TableCell>
                    <TableCell className="text-muted-foreground font-mono">{video.duration || '--'}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="hover:bg-primary/20 hover:text-primary transition-colors disabled:opacity-50 text-zinc-300" disabled={video.status !== 'completed'}>
                        Xem chi tiết
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </Card>
    </div>
  )
}
