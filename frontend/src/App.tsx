import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Video, Settings } from 'lucide-react'
import { Dashboard } from '@/pages/Dashboard'
import { Create } from '@/pages/Create'
import { Admin } from '@/pages/Admin'
import { Toaster } from '@/components/ui/sonner'

const queryClient = new QueryClient()

function Sidebar() {
  const location = useLocation();
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Create', path: '/create', icon: Video },
    { name: 'Admin', path: '/admin', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-background border-r p-6 flex flex-col gap-6 h-full">
      <div className="font-bold text-2xl tracking-tight">WebReel</div>
      <nav className="flex flex-col gap-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link 
              key={item.path} 
              to={item.path} 
              className={`flex items-center gap-3 px-4 py-2 rounded-md text-sm font-medium transition-colors ${isActive ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
            >
              <item.icon className="w-4 h-4" />
              {item.name}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-background flex text-foreground">
          <Sidebar />
          <main className="flex-1 p-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/create" element={<Create />} />
              <Route path="/admin" element={<Admin />} />
            </Routes>
          </main>
        </div>
        <Toaster theme="dark" />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
