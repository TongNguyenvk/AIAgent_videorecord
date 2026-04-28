import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import * as z from "zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { createVideo } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Loader2, Wand2 } from "lucide-react"

const formSchema = z.object({
  prompt: z.string().min(5, { message: "Prompt phải có ít nhất 5 ký tự." }),
  tts_engine: z.string(),
  tts_voice: z.string(),
  padding_ms: z.coerce.number().min(0).max(5000),
  enable_tts: z.boolean().default(true),
  enable_review: z.boolean().default(false),
})

export function Create() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      prompt: "",
      tts_engine: "edge",
      tts_voice: "vi-VN-HoaiMyNeural",
      padding_ms: 500,
      enable_tts: true,
      enable_review: false,
    },
  })

  const mutation = useMutation({
    mutationFn: createVideo,
    onSuccess: () => {
      toast.success("Đã tạo Job thành công!", {
        description: "Hệ thống đã ghi nhận và đang đưa vào hàng đợi."
      });
      // Ép Dashboard gọi API lại (hoặc reload mock local)
      queryClient.invalidateQueries({ queryKey: ['videos'] })
      // Navigate thẳng về Dashboard để user thấy trạng thái Pending
      navigate("/")
    },
    onError: () => {
      toast.error("Lỗi mất rồi", {
        description: "Không thể kết nối với server."
      })
    }
  })

  function onSubmit(values: z.infer<typeof formSchema>) {
    mutation.mutate(values)
  }

  return (
    <div className="max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-8">
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-primary to-primary/50 bg-clip-text text-transparent">Chỉ đạo sản xuất</h1>
        <p className="text-muted-foreground mt-2 text-lg">Cung cấp ý tưởng, Agent sẽ tự động clone voice, generate ảnh và dựng thành thước phim hoàn chỉnh.</p>
      </div>

      <Card className="border-white/10 bg-black/40 backdrop-blur-xl shadow-2xl">
        <CardHeader>
          <CardTitle className="text-white">Setting Video Pipeline</CardTitle>
          <CardDescription>Thiết lập tham số cho OS Automation và AI Worker</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              
              <FormField
                control={form.control}
                name="prompt"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-zinc-300">Prompt / Ý tưởng kịch bản</FormLabel>
                    <FormControl>
                      <Input placeholder="Ví dụ: Hướng dẫn cài đặt mạng neural từ con số 0..." className="bg-white/5 border-white/10 text-white placeholder:text-zinc-600 focus-visible:ring-primary h-12" {...field} />
                    </FormControl>
                    <FormDescription className="text-zinc-500">
                      Càng chi tiết, WebReel lên kịch bản càng mượt.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <FormField
                  control={form.control}
                  name="tts_engine"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-zinc-300">TTS Engine</FormLabel>
                      <FormControl>
                        <select className="flex h-12 w-full items-center justify-between rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 text-white" {...field}>
                          <option value="edge" className="bg-zinc-900">Edge TTS</option>
                          <option value="fpt" className="bg-zinc-900">FPT.AI</option>
                        </select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="tts_voice"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-zinc-300">Voice Model</FormLabel>
                      <FormControl>
                         <Input className="bg-white/5 border-white/10 text-white focus-visible:ring-primary h-12" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="padding_ms"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-zinc-300">Padding Delay (ms)</FormLabel>
                      <FormControl>
                         <Input type="number" className="bg-white/5 border-white/10 text-white focus-visible:ring-primary h-12" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="flex items-center gap-6 p-4 rounded-lg bg-white/5 border border-white/10">
                <FormField
                  control={form.control}
                  name="enable_tts"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-3 space-y-0">
                      <FormControl>
                        <input type="checkbox" className="w-5 h-5 accent-primary" checked={field.value} onChange={field.onChange} />
                      </FormControl>
                      <FormLabel className="text-zinc-300 font-medium cursor-pointer">Bật Voice (TTS)</FormLabel>
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="enable_review"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-3 space-y-0">
                      <FormControl>
                        <input type="checkbox" className="w-5 h-5 accent-primary" checked={field.value} onChange={field.onChange} />
                      </FormControl>
                      <FormLabel className="text-zinc-300 font-medium cursor-pointer">Tạm dừng để Review Kịch Bản</FormLabel>
                    </FormItem>
                  )}
                />
              </div>

              <div className="pt-4 flex justify-end">
                <Button 
                  type="submit" 
                  size="lg" 
                  disabled={mutation.isPending}
                  className="rounded-full shadow-lg shadow-primary/20 w-full sm:w-auto hover:scale-[1.02] active:scale-[0.98] transition-all"
                >
                  {mutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Đang xử lý Job...
                    </>
                  ) : (
                    <>
                      <Wand2 className="mr-2 h-5 w-5" />
                      Render File
                    </>
                  )}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}
