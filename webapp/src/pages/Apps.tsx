import { api } from "../lib/api";
import { useAsync } from "./Console";

// Fleet apps view: robot companions with live probe state. Full dynamic
// fleet discovery (GET /api/fleet/apps + registry filter) is a follow-up —
// this page shows real companion data today, not a fake app grid.
export default function Apps() {
  const companions = useAsync(() => api.companions().then((r) => r.data.companions));

  return (
    <div data-testid="apps-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Apps — companions & fleet</h1>
      {companions.loading && <div className="text-sm text-zinc-300">Loading companions…</div>}
      <div className="grid gap-3 md:grid-cols-2">
        {(companions.data ?? []).map((c) => (
          <div key={c.id} className="rounded border border-zinc-800 bg-zinc-900 p-4">
            <div className="flex items-center justify-between">
              <b>{c.label}</b>
              <span
                className={`rounded px-2 py-0.5 text-sm ${c.status === "live" ? "bg-emerald-900 text-emerald-200" : "bg-zinc-800 text-zinc-300"}`}
              >
                {c.status}
              </span>
            </div>
            <div className="mt-1 text-sm text-zinc-300">
              Repo: {c.repo} · Mount: {c.mount}
            </div>
            {c.status === "live" && (
              <a
                href={c.dashboard_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-block rounded bg-zinc-800 px-3 py-1 text-sm text-cyan-200 hover:bg-zinc-700"
              >
                Open dashboard
              </a>
            )}
          </div>
        ))}
      </div>
      <div className="rounded border border-zinc-800 p-3 text-sm text-zinc-400">
        Fleet port registry: mcp-central-docs/operations/WEBAPP_PORTS.md — lidar-mcp: SSE 11075, API
        11217, web 11218.
      </div>
    </div>
  );
}
