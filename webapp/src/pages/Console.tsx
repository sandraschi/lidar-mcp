import { useEffect, useState } from "react";
import PolarPlot from "../components/PolarPlot";
import { api, type ScanData } from "../lib/api";

function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true);
    fn()
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, error, loading };
}

export { useAsync };

export default function Console() {
  const [port, setPort] = useState("");
  const [scan, setScan] = useState<ScanData | null>(null);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const ports = useAsync(() => api.ports().then((r) => r.data.ports));

  const runStatus = async () => {
    setBusy(true);
    try {
      const r = await fetch("/api/status").then((x) => x.json());
      setStatus(JSON.stringify(r, null, 2));
    } catch (e) {
      setStatus(String(e));
    } finally {
      setBusy(false);
    }
  };

  const runScan = async () => {
    setBusy(true);
    try {
      const r = await api.scan(3.0, port);
      if (r.success) setScan(r.data);
      else setStatus(r.message);
    } catch (e) {
      setStatus(String(e));
    } finally {
      setBusy(false);
    }
  };

  const saveScan = async () => {
    if (!note) return;
    setBusy(true);
    try {
      const r = await api.saveScan(note, 3.0, port);
      setStatus(r.success ? `Saved ${r.data.scan_id}` : r.message);
      setNote("");
    } catch (e) {
      setStatus(String(e));
    } finally {
      setBusy(false);
    }
  };

  const valid = scan?.points.filter((p) => p.is_valid) ?? [];
  const dists = valid.map((p) => p.distance_mm);
  // Real hardware scans can carry thousands of points — spreading into
  // Math.min/max(...) overflows the call stack, so reduce instead.
  const minDist = dists.length ? dists.reduce((a, b) => Math.min(a, b)) : 0;
  const maxDist = dists.length ? dists.reduce((a, b) => Math.max(a, b)) : 0;
  const rangeMax = dists.length ? maxDist * 1.1 : 4000;

  return (
    <div data-testid="console-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Console — is my module alive?</h1>
      {ports.loading && <div className="text-sm text-zinc-300">Probing serial ports…</div>}
      {ports.error && (
        <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">
          Ports failed: {ports.error}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-zinc-300" htmlFor="port-select">
          Serial port
        </label>
        <select
          id="port-select"
          data-testid="port-select"
          value={port}
          onChange={(e) => setPort(e.target.value)}
          className="px-2 py-1"
        >
          <option value="">auto (LIDAR_PORT)</option>
          {(ports.data ?? []).map((p) => (
            <option key={p.port} value={p.port}>
              {p.port} — {p.description}
            </option>
          ))}
        </select>
        <button
          data-testid="status-button"
          onClick={runStatus}
          disabled={busy}
          className="rounded bg-zinc-800 px-3 py-1 text-sm hover:bg-zinc-700 disabled:opacity-50"
        >
          Status
        </button>
        <button
          data-testid="scan-button"
          onClick={runScan}
          disabled={busy}
          className="rounded bg-cyan-700 px-3 py-1 text-sm hover:bg-cyan-600 disabled:opacity-50"
        >
          {busy ? "Scanning…" : "Scan once"}
        </button>
      </div>
      {scan && (
        <div data-testid="status-card" className="flex flex-wrap gap-4">
          <PolarPlot points={scan.points} rangeMaxMm={rangeMax} />
          <div className="space-y-2 text-sm">
            <div className="rounded border border-zinc-800 bg-zinc-900 p-3">
              <div className="text-zinc-300">
                Points: {scan.point_count} ({valid.length} valid)
              </div>
              <div className="text-zinc-300">
                Range: {dists.length ? `${minDist.toFixed(0)}–${maxDist.toFixed(0)} mm` : "—"}
              </div>
              <div className="text-zinc-300">Duration: {scan.duration_ms.toFixed(0)} ms</div>
            </div>
            <div className="flex gap-2">
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="note for save…"
                className="rounded px-2 py-1 text-sm"
              />
              <button
                onClick={saveScan}
                disabled={busy || !note}
                className="rounded bg-zinc-800 px-3 py-1 text-sm hover:bg-zinc-700 disabled:opacity-50"
              >
                Save scan
              </button>
            </div>
          </div>
        </div>
      )}
      {status && (
        <pre className="overflow-x-auto rounded border border-zinc-800 bg-zinc-900 p-3 text-sm">
          {status}
        </pre>
      )}
      {!scan && !status && !busy && (
        <div className="rounded border border-zinc-800 p-6 text-sm text-zinc-300">
          Pick a port (or leave auto), hit <b>Status</b> for firmware/health, <b>Scan once</b> for a
          360° sweep.
        </div>
      )}
    </div>
  );
}
