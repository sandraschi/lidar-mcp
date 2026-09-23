import { useState } from "react";
import { api } from "../lib/api";
import { useAsync } from "./Console";

export default function DiffLab() {
  const scans = useAsync(() => api.scans().then((r) => r.data.scans));
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [sectorDeg, setSectorDeg] = useState(5);
  const [toleranceMm, setToleranceMm] = useState(150);
  const [result, setResult] = useState<{ changed_count: number; changed: { sector_deg: number; delta_mm: number | null }[] } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (!a || !b) return;
    setBusy(true);
    setError("");
    try {
      const r = await api.diff({ scan_a: a, scan_b: b, sector_deg: sectorDeg, tolerance_mm: toleranceMm });
      if (r.success) setResult({ changed_count: r.data.changed_count, changed: r.data.changed });
      else setError(r.message);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const maxDelta = Math.max(1, ...((result?.changed ?? []).map((c) => Math.abs(c.delta_mm ?? 0))));

  return (
    <div data-testid="diff-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Diff Lab — what moved?</h1>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="text-zinc-300">A
          <select data-testid="diff-a" value={a} onChange={(e) => setA(e.target.value)} className="ml-2 px-2 py-1">
            <option value="">pick…</option>
            {(scans.data ?? []).map((s) => <option key={s.scan_id} value={s.scan_id}>{s.scan_id} — {s.note}</option>)}
          </select>
        </label>
        <label className="text-zinc-300">B
          <select data-testid="diff-b" value={b} onChange={(e) => setB(e.target.value)} className="ml-2 px-2 py-1">
            <option value="">pick…</option>
            {(scans.data ?? []).map((s) => <option key={s.scan_id} value={s.scan_id}>{s.scan_id} — {s.note}</option>)}
          </select>
        </label>
        <label className="text-zinc-300">sector°
          <input type="number" value={sectorDeg} onChange={(e) => setSectorDeg(Number(e.target.value))} className="ml-2 w-20 px-1" />
        </label>
        <label className="text-zinc-300">tolerance mm
          <input type="number" value={toleranceMm} onChange={(e) => setToleranceMm(Number(e.target.value))} className="ml-2 w-24 px-1" />
        </label>
        <button data-testid="diff-run" onClick={run} disabled={busy || !a || !b} className="rounded bg-cyan-700 px-3 py-1 hover:bg-cyan-600 disabled:opacity-50">
          {busy ? "Diffing…" : "Compare"}
        </button>
      </div>
      {error && <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">{error}</div>}
      {result && (
        <div className="space-y-1" data-testid="diff-result">
          <div className="text-sm text-zinc-300">{result.changed_count} sectors changed beyond tolerance.</div>
          {result.changed.slice(0, 24).map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span className="w-20 font-mono text-zinc-300">{c.sector_deg.toFixed(0)}°</span>
              <div className="h-3 flex-1 rounded bg-zinc-800">
                <div className="h-3 rounded bg-amber-500" style={{ width: `${(Math.abs(c.delta_mm ?? 0) / maxDelta) * 100}%` }} />
              </div>
              <span className="w-28 text-right font-mono text-zinc-300">{c.delta_mm === null ? "appeared/cleared" : `${(c.delta_mm > 0 ? "+" : "")}${c.delta_mm.toFixed(0)} mm`}</span>
            </div>
          ))}
        </div>
      )}
      {(!result && !error) && <div className="rounded border border-zinc-800 p-6 text-sm text-zinc-300">Pick two saved scans — e.g. door open vs door closed — and compare.</div>}
    </div>
  );
}
