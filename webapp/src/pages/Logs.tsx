import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface Entry {
  ts: string;
  level: string;
  logger: string;
  message: string;
}

export default function Logs() {
  const [logs, setLogs] = useState<Entry[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const r = await api.logs();
      setLogs(r.data.logs);
      setError("");
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    load();
    const t = window.setInterval(load, 5000);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shown = logs.filter(
    (l) => !filter || `${l.level} ${l.logger} ${l.message}`.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <div data-testid="logs-page" className="space-y-3">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">Logs — backend ring buffer</h1>
        <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="filter… (Ctrl+L)" className="rounded px-2 py-1 text-sm" />
        <button onClick={() => {
          const blob = new Blob([shown.map((l) => `${l.ts} ${l.level} ${l.logger} ${l.message}`).join("\n")], { type: "text/plain" });
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = "lidar-logs.txt";
          a.click();
        }} className="rounded bg-zinc-800 px-2 py-1 text-sm hover:bg-zinc-700">Export</button>
      </div>
      {error && <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">{error}</div>}
      <pre className="max-h-[60vh] overflow-y-auto rounded border border-zinc-800 bg-zinc-950 p-3 text-sm">
        {shown.length === 0 ? "No entries yet — run a scan." : shown.map((l, i) => (
          <div key={i}>
            <span className="text-zinc-500">{l.ts}</span> <span className={l.level === "ERROR" || l.level === "WARNING" ? "text-amber-300" : "text-cyan-200"}>{l.level}</span>{" "}
            <span className="text-zinc-400">{l.logger}</span> {l.message}
          </div>
        ))}
      </pre>
    </div>
  );
}
