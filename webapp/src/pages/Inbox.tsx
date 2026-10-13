import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAsync } from "./Console";

interface Item {
  key: string;
  kind: "scan" | "log";
  title: string;
  detail: string;
  to: string;
}

export default function Inbox() {
  const [query, setQuery] = useState("");
  const scans = useAsync(() => api.scans().then((r) => r.data.scans));
  const logs = useAsync(() => api.logs().then((r) => r.data.logs));

  const items: Item[] = [
    ...((scans.data ?? []).map((s) => ({
      key: `scan-${s.scan_id}`,
      kind: "scan" as const,
      title: s.scan_id,
      detail: `${s.note || "no note"} · ${s.valid_count}/${s.point_count} valid · ${s.saved_at}`,
      to: "/library",
    })) ?? []),
    ...((logs.data ?? [])
      .filter((l) => l.level === "WARNING" || l.level === "ERROR")
      .slice(-30)
      .map((l, i) => ({
        key: `log-${i}-${l.ts}`,
        kind: "log" as const,
        title: `${l.level} · ${l.logger}`,
        detail: `${l.ts} — ${l.message}`,
        to: "/logs",
      })) ?? []),
  ];

  const q = query.trim().toLowerCase();
  const shown = q
    ? items.filter(
        (it) => it.title.toLowerCase().includes(q) || it.detail.toLowerCase().includes(q),
      )
    : items;

  return (
    <div data-testid="inbox-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Inbox — recent activity</h1>
      <div className="flex items-center gap-3">
        <input
          data-testid="inbox-filter"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter activity…"
          className="w-64 rounded bg-zinc-900 px-3 py-1.5 text-sm"
        />
        <span data-testid="inbox-count" className="text-sm text-zinc-400">
          {shown.length} of {items.length} items
        </span>
      </div>
      {(scans.loading || logs.loading) && (
        <div className="text-sm text-zinc-300">Loading activity…</div>
      )}
      {(scans.error || logs.error) && (
        <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">
          Failed: {scans.error ?? logs.error}
        </div>
      )}
      {items.length === 0 && !scans.loading && !logs.loading && (
        <div className="rounded border border-zinc-800 p-6 text-sm text-zinc-300">
          Nothing yet. Capture a scan from the{" "}
          <Link to="/console" className="text-cyan-300">
            Console
          </Link>{" "}
          and it will appear here.
        </div>
      )}
      {items.length > 0 && shown.length === 0 && (
        <div className="rounded border border-zinc-800 p-6 text-sm text-zinc-300">
          No activity matches &ldquo;{query}&rdquo;.
        </div>
      )}
      <div className="space-y-2">
        {shown.map((it) => (
          <Link
            key={it.key}
            to={it.to}
            data-testid={`inbox-item-${it.kind}`}
            className="block rounded border border-zinc-800 bg-zinc-900 p-3 text-sm hover:border-cyan-700"
          >
            <div className="font-mono text-cyan-200">{it.title}</div>
            <div className="text-zinc-300">{it.detail}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
