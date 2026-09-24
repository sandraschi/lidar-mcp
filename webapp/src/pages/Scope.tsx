import { useEffect, useRef, useState } from "react";
import PolarPlot from "../components/PolarPlot";
import { api, type ScanData } from "../lib/api";

export default function Scope() {
  const [live, setLive] = useState(false);
  const [scan, setScan] = useState<ScanData | null>(null);
  const [error, setError] = useState("");
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!live) {
      if (timer.current) window.clearInterval(timer.current);
      return;
    }
    const tick = async () => {
      try {
        const r = await api.scan(1.2);
        if (r.success) {
          setScan(r.data);
          setError("");
        } else {
          setError(r.message);
        }
      } catch (e) {
        setError(String(e));
      }
    };
    tick();
    timer.current = window.setInterval(tick, 2500);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [live]);

  const valid = scan?.points.filter((p) => p.is_valid) ?? [];
  const dists = valid.map((p) => p.distance_mm);
  // Real hardware scans can carry thousands of points — spreading into
  // Math.min/max(...) overflows the call stack, so reduce instead.
  const minDist = dists.length ? dists.reduce((a, b) => Math.min(a, b)) : 0;
  const maxDist = dists.length ? dists.reduce((a, b) => Math.max(a, b)) : 0;
  const rangeMax = dists.length ? maxDist * 1.1 : 4000;

  return (
    <div data-testid="scope-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Scope — live polar view</h1>
      <div className="flex gap-3">
        {!live ? (
          <button
            data-testid="scope-start"
            onClick={() => setLive(true)}
            className="rounded bg-cyan-700 px-4 py-1 text-sm hover:bg-cyan-600"
          >
            Start stream
          </button>
        ) : (
          <button
            data-testid="scope-stop"
            onClick={() => setLive(false)}
            className="rounded bg-red-800 px-4 py-1 text-sm hover:bg-red-700"
          >
            Stop
          </button>
        )}
        <span className="text-sm text-zinc-300">
          1.2 s captures, ~2.5 s cadence — demo-grade streaming over REST polling.
        </span>
      </div>
      {error && <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">{error}</div>}
      {scan ? (
        <div className="flex flex-wrap gap-4">
          <PolarPlot points={scan.points} rangeMaxMm={rangeMax} />
          <div className="space-y-1 text-sm text-zinc-300">
            <div>
              Points: {scan.point_count} ({valid.length} valid)
            </div>
            <div>Closest: {dists.length ? `${minDist.toFixed(0)} mm` : "—"}</div>
            <div>Capture: {scan.duration_ms.toFixed(0)} ms</div>
          </div>
        </div>
      ) : (
        !error && (
          <div className="rounded border border-zinc-800 p-6 text-sm text-zinc-300">
            Press Start stream for a live sweep.
          </div>
        )
      )}
    </div>
  );
}
