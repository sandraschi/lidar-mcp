import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  BookOpen,
  Bot,
  Brain,
  Camera,
  ChevronLeft,
  ChevronRight,
  Cpu,
  FlaskConical,
  LayoutDashboard,
  LifeBuoy,
  Radar,
  ScanLine,
  ScrollText,
  Settings,
  Shapes,
  Terminal,
  Wrench,
} from "lucide-react";
import { waitForBackend } from "../lib/api";

const NAV: { group: string; items: { to: string; label: string; icon: React.ReactNode; testid: string }[] }[] = [
  {
    group: "Overview",
    items: [
      { to: "/", label: "Dashboard", icon: <LayoutDashboard size={18} />, testid: "nav-dashboard" },
      { to: "/console", label: "Console", icon: <Terminal size={18} />, testid: "nav-console" },
    ],
  },
  {
    group: "Mapping",
    items: [
      { to: "/scope", label: "Scope", icon: <Radar size={18} />, testid: "nav-scope" },
      { to: "/mapper", label: "Mapper", icon: <Shapes size={18} />, testid: "nav-mapper" },
      { to: "/diff", label: "Diff Lab", icon: <FlaskConical size={18} />, testid: "nav-diff" },
      { to: "/ptz3d", label: "PTZ 3D", icon: <Camera size={18} />, testid: "nav-ptz3d" },
      { to: "/library", label: "Scan Library", icon: <BookOpen size={18} />, testid: "nav-library" },
    ],
  },
  {
    group: "Robot",
    items: [{ to: "/raspbots", label: "Raspbot Link", icon: <Bot size={18} />, testid: "nav-raspbots" }],
  },
  {
    group: "Fleet",
    items: [
      { to: "/tools", label: "Tools", icon: <Wrench size={18} />, testid: "nav-tools" },
      { to: "/skills", label: "Skills", icon: <Brain size={18} />, testid: "nav-skills" },
      { to: "/apps", label: "Apps", icon: <Shapes size={18} />, testid: "nav-apps" },
      { to: "/chat", label: "Chat", icon: <Activity size={18} />, testid: "nav-chat" },
      { to: "/api-docs", label: "API Docs", icon: <ScrollText size={18} />, testid: "nav-api-docs" },
    ],
  },
  {
    group: "System",
    items: [
      { to: "/settings", label: "Settings", icon: <Settings size={18} />, testid: "nav-settings" },
      { to: "/help", label: "Help", icon: <LifeBuoy size={18} />, testid: "nav-help" },
      { to: "/logs", label: "Logs", icon: <Cpu size={18} />, testid: "nav-logs" },
    ],
  },
];

export function BackendDot({ testid = "backend-dot" }: { testid?: string }) {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    waitForBackend((state) => setOk(state));
    const t = setInterval(() => {
      fetch("/api/health")
        .then((r) => setOk(r.ok))
        .catch(() => setOk(false));
    }, 15000);
    return () => clearInterval(t);
  }, []);
  const color = ok === null ? "bg-zinc-500 animate-pulse" : ok ? "bg-emerald-400" : "bg-red-400";
  const label = ok === null ? "Probing…" : ok ? "Backend connected" : "Backend unreachable";
  return (
    <span data-testid={testid} title={label} className="flex items-center gap-2 text-sm text-zinc-300">
      <span data-testid="backend-dot" className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
      {label}
    </span>
  );
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const loc = useLocation();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && (e.key === "l" || e.key === "L")) {
        e.preventDefault();
        window.location.hash = "#/logs";
      }
      if (e.ctrlKey && (e.key === "h" || e.key === "H")) {
        e.preventDefault();
        window.location.hash = "#/help";
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div data-testid="dashboard" className="flex h-full bg-zinc-950 text-zinc-100">
      <aside className={`${collapsed ? "w-16" : "w-60"} border-r border-zinc-800 bg-zinc-900/60 backdrop-blur transition-all`}>
        <div className="flex items-center justify-between border-b border-zinc-800 p-3">
          {!collapsed && (
            <Link to="/" className="flex items-center gap-2 font-semibold">
              <ScanLine size={20} className="text-cyan-300" />
              <span>lidar-mcp</span>
              <span className="text-sm text-zinc-400">v0.4</span>
            </Link>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="rounded p-1 text-zinc-300 hover:bg-zinc-800"
            aria-label="Toggle sidebar"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
        <nav className="overflow-y-auto p-2">
          {NAV.map((g) => (
            <div key={g.group} className="mb-3">
              {!collapsed && <div className="px-2 pb-1 text-sm uppercase tracking-wide text-zinc-400">{g.group}</div>}
              {g.items.map((it) => {
                const active = loc.pathname === it.to;
                return (
                  <Link
                    key={it.to}
                    to={it.to}
                    data-testid={it.testid}
                    className={`mb-0.5 flex items-center gap-3 rounded px-2 py-2 text-sm ${
                      active ? "bg-zinc-800 text-cyan-200" : "text-zinc-300 hover:bg-zinc-800/60"
                    }`}
                    title={it.label}
                  >
                    {it.icon}
                    {!collapsed && <span>{it.label}</span>}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="border-t border-zinc-800 p-3">
          <BackendDot />
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/60 px-4 py-2">
          <div className="text-sm text-zinc-300">YDLIDAR console · 11217/11218</div>
          <div className="flex items-center gap-4">
            <BackendDot testid="backend-dot-top" />
            <Link to="/help" className="text-sm text-zinc-300 hover:text-cyan-200" title="Help (Ctrl+H)">
              ?
            </Link>
            <Link to="/logs" className="text-sm text-zinc-300 hover:text-cyan-200" title="Logs (Ctrl+L)">
              Logs
            </Link>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
