import { useState } from "react";
import { api } from "../lib/api";

interface Slice {
  panDeg: number;
  scanId: string;
  closestMm: number | null;
}

// Guided capture for the PTZ-vertical-fan hack: one YDLIDAR rotated 90° so
// its sweep traces a VERTICAL circle, panned horizontally slice by slice.
// Slow (~seconds per full sweep), glorious, $50 3D. Assembly of slices into
// a real point cloud happens in the agent/LeWM pipeline — this page owns
// honest capture + a closest-return heat strip per slice.
export default function Ptz3D() {
  const [panStart, setPanStart] = useState(0);
  const [panStop, setPanStop] = useState(60);
  const [panStep, setPanStep] = useState(5);
  const [slices, setSlices] = useState<Slice[]>([]);
  const [at, setAt] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const plan: number[] = [];
  for (let p = panStart; p <= panStop + 1e-9; p += panStep) plan.push(Number(p.toFixed(2)));

  const captureAll = async () => {
    setBusy(true);
    setError("");
    setSlices([]);
    try {
      const done: Slice[] = [];
      for (const pan of plan) {
        setAt(pan);
        const r = await api.saveScan(`ptz3d pan=${pan}`, 3.0);
        if (!r.success) throw new Error(r.message);
        const pts = (r.data.points ?? []).filter((p) => p.is_valid).map((p) => p.distance_mm);
        // Real hardware scans can carry thousands of points — spreading into
        // Math.min(...) overflows the call stack, so reduce instead.
        done.push({
          panDeg: pan,
          scanId: r.data.scan_id,
          closestMm: pts.length ? pts.reduce((a, b) => Math.min(a, b)) : null,
        });
        setSlices([...done]);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
      setAt(null);
    }
  };

  return (
    <div data-testid="ptz3d-page" className="space-y-4">
      <h1 className="text-xl font-semibold">PTZ 3D — the $50 vertical fan</h1>
      <p className="max-w-3xl text-sm text-zinc-300">
        Mount the LiDAR sideways on a pan servo, sweep the pan in steps, capture one vertical fan
        per step. This page captures and logs slices; stitching slices into a 3D cloud is the
        agent's job (see llms-full.txt § PTZ).
      </p>
      {error && <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">{error}</div>}
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="text-zinc-300">
          pan from°
          <input
            type="number"
            value={panStart}
            onChange={(e) => setPanStart(Number(e.target.value))}
            className="ml-2 w-20 px-1"
          />
        </label>
        <label className="text-zinc-300">
          to°
          <input
            type="number"
            value={panStop}
            onChange={(e) => setPanStop(Number(e.target.value))}
            className="ml-2 w-20 px-1"
          />
        </label>
        <label className="text-zinc-300">
          step°
          <input
            type="number"
            value={panStep}
            min={1}
            onChange={(e) => setPanStep(Number(e.target.value))}
            className="ml-2 w-20 px-1"
          />
        </label>
        <span className="text-zinc-400">{plan.length} slices planned</span>
        <button
          data-testid="ptz3d-capture"
          onClick={captureAll}
          disabled={busy || plan.length === 0}
          className="rounded bg-cyan-700 px-3 py-1 hover:bg-cyan-600 disabled:opacity-50"
        >
          {busy ? `Capturing pan ${at}°… (move the servo now)` : "Capture slices"}
        </button>
      </div>
      {busy && (
        <div className="text-sm text-amber-200">
          Manual rig: set the pan servo to {at}° while each capture runs. Motorised pan sync is
          future work.
        </div>
      )}
      {slices.length > 0 && (
        <div className="space-y-1" data-testid="ptz3d-slices">
          {slices.map((s) => (
            <div key={s.scanId} className="flex items-center gap-2 text-sm">
              <span className="w-20 font-mono text-zinc-300">{s.panDeg}°</span>
              <span className="font-mono text-cyan-200">{s.scanId}</span>
              <span className="text-zinc-300">
                {s.closestMm === null ? "no returns" : `closest ${s.closestMm.toFixed(0)} mm`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
