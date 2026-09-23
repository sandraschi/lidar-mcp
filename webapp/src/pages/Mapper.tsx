import { useRef, useState } from "react";
import { api, type ScanPoint } from "../lib/api";

interface Pose {
  x: number;
  y: number;
  thetaDeg: number;
  scanId: string;
  note: string;
}

// Honest label: pose-tagged scan stitching. The robot (or your hands)
// supplies the pose per capture; the page transforms each scan's valid
// returns into one global frame. This is NOT full SLAM — no loop closure,
// no particle filter. Drift in, drift out.
export default function Mapper() {
  const [poses, setPoses] = useState<Pose[]>([{ x: 0, y: 0, thetaDeg: 0, scanId: "", note: "" }]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [built, setBuilt] = useState<{ x: number; y: number }[] | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const setPose = (i: number, patch: Partial<Pose>) =>
    setPoses((ps) => ps.map((p, j) => (j === i ? { ...p, ...patch } : p)));

  const capture = async (i: number) => {
    const p = poses[i];
    setBusy(true);
    setError("");
    try {
      const r = await api.saveScan(p.note || `pose-${i}`, 3.0);
      if (r.success) setPose(i, { scanId: r.data.scan_id });
      else setError(r.message);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const build = async () => {
    setBusy(true);
    setError("");
    try {
      const pts: { x: number; y: number }[] = [];
      for (const p of poses) {
        if (!p.scanId) continue;
        const resp = await fetch(`/api/scans/${encodeURIComponent(p.scanId)}`);
        const body = await resp.json();
        if (!body.success) throw new Error(body.message);
        pts.push(...transformPoints(body.data.points as ScanPoint[], p));
      }
      setBuilt(pts);
      drawMap(pts);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const drawMap = (pts: { x: number; y: number }[]) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = "#09090b";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (!pts.length) return;
    const xs = pts.map((p) => p.x);
    const ys = pts.map((p) => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const span = Math.max(maxX - minX, maxY - minY, 0.5);
    const scale = (Math.min(canvas.width, canvas.height) - 40) / span;
    ctx.fillStyle = "#22d3ee";
    for (const p of pts) {
      ctx.fillRect(20 + (p.x - minX) * scale - 1, 20 + (maxY - p.y) * scale - 1, 2, 2);
    }
    // Pose markers (amber): where each capture stood.
    ctx.fillStyle = "#f59e0b";
    for (const p of poses) {
      if (!p.scanId) continue;
      ctx.beginPath();
      ctx.arc(20 + (p.x - minX) * scale, 20 + (maxY - p.y) * scale, 5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = "#71717a";
    ctx.font = "12px sans-serif";
    ctx.fillText(
      `${pts.length} stitched points · span ${span.toFixed(1)} m`,
      12,
      canvas.height - 10,
    );
  };

  return (
    <div data-testid="mapper-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Mapper — pose-tagged stitching (not SLAM)</h1>
      <p className="max-w-3xl text-sm text-zinc-300">
        Drive the sensor (or the Raspbot) to several poses, capture a scan at each, then stitch.
        Poses come from you or robot odometry — the page trusts them blindly. No loop closure, no
        filter: drift in, drift out.
      </p>
      {error && <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">{error}</div>}
      <div className="space-y-2">
        {poses.map((p, i) => (
          <div
            key={i}
            className="flex flex-wrap items-center gap-2 rounded border border-zinc-800 bg-zinc-900 p-2 text-sm"
          >
            <span className="text-zinc-400">#{i}</span>
            <label className="text-zinc-300">
              x(m)
              <input
                data-testid={`pose-x-${i}`}
                type="number"
                step="0.1"
                value={p.x}
                onChange={(e) => setPose(i, { x: Number(e.target.value) })}
                className="ml-1 w-20 px-1"
              />
            </label>
            <label className="text-zinc-300">
              y(m)
              <input
                data-testid={`pose-y-${i}`}
                type="number"
                step="0.1"
                value={p.y}
                onChange={(e) => setPose(i, { y: Number(e.target.value) })}
                className="ml-1 w-20 px-1"
              />
            </label>
            <label className="text-zinc-300">
              θ°
              <input
                data-testid={`pose-t-${i}`}
                type="number"
                step="5"
                value={p.thetaDeg}
                onChange={(e) => setPose(i, { thetaDeg: Number(e.target.value) })}
                className="ml-1 w-20 px-1"
              />
            </label>
            <input
              value={p.note}
              onChange={(e) => setPose(i, { note: e.target.value })}
              placeholder="note"
              className="px-2 py-0.5 text-sm"
            />
            <button
              onClick={() => capture(i)}
              disabled={busy}
              className="rounded bg-zinc-800 px-2 py-0.5 hover:bg-zinc-700 disabled:opacity-50"
            >
              {p.scanId ? "Re-capture" : "Capture"}
            </button>
            {p.scanId && <span className="font-mono text-sm text-cyan-200">{p.scanId}</span>}
          </div>
        ))}
        <div className="flex gap-2">
          <button
            onClick={() =>
              setPoses((ps) => [...ps, { x: 0, y: 0, thetaDeg: 0, scanId: "", note: "" }])
            }
            className="rounded bg-zinc-800 px-3 py-1 text-sm hover:bg-zinc-700"
          >
            Add pose
          </button>
          <button
            data-testid="mapper-build"
            onClick={build}
            disabled={busy}
            className="rounded bg-cyan-700 px-3 py-1 text-sm hover:bg-cyan-600 disabled:opacity-50"
          >
            Build map
          </button>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        width={640}
        height={480}
        className="rounded border border-zinc-800"
        data-testid="mapper-canvas"
      />
      {built && built.length === 0 && (
        <div className="text-sm text-zinc-300">
          No stitched points yet — capture at least one pose, then build.
        </div>
      )}
    </div>
  );
}

export function transformPoints(points: ScanPoint[], pose: Pose): { x: number; y: number }[] {
  const t = (pose.thetaDeg * Math.PI) / 180;
  return points
    .filter((p) => p.is_valid)
    .map((p) => {
      const a = (p.angle_deg * Math.PI) / 180;
      const lx = (p.distance_mm / 1000) * Math.sin(a);
      const ly = (p.distance_mm / 1000) * Math.cos(a);
      return {
        x: pose.x + lx * Math.cos(t) - ly * Math.sin(t),
        y: pose.y + lx * Math.sin(t) + ly * Math.cos(t),
      };
    });
}
