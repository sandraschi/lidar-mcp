import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface Companion {
  id: string;
  label: string;
  repo: string;
  health_url: string;
  dashboard_url: string;
  mount: string;
  status: string;
}

const SECTORS = 8;

export default function Raspbots() {
  const [companions, setCompanions] = useState<Companion[]>([]);
  const [probe, setProbe] = useState<
    Record<
      string,
      {
        online: boolean;
        latency_ms: number | null;
        planned?: boolean;
        detail?: string;
      }
    >
  >({});
  const [sectors, setSectors] = useState<(number | null)[]>([]);
  const [guardMm, setGuardMm] = useState(400);
  const [tripped, setTripped] = useState(false);
  const [watching, setWatching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .companions()
      .then((r) => setCompanions(r.data.companions))
      .catch(() => setCompanions([]));
  }, []);

  const probeOne = async (id: string) => {
    try {
      const r = await api.companion(id);
      setProbe((p) => ({
        ...p,
        [id]: {
          online: r.data.online,
          latency_ms: r.data.latency_ms,
          planned: r.data.planned,
        },
      }));
    } catch (e) {
      setProbe((p) => ({ ...p, [id]: { online: false, latency_ms: null } }));
      setError(String(e));
    }
  };

  useEffect(() => {
    companions.forEach((c) => {
      if (c.status === "live") probeOne(c.id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companions]);

  useEffect(() => {
    if (!watching || tripped) return;
    const t = window.setInterval(async () => {
      try {
        const r = await api.scan(1.2);
        if (!r.success) return;
        const width = 360 / SECTORS;
        const mins: (number | null)[] = Array(SECTORS).fill(null);
        for (const p of r.data.points) {
          if (!p.is_valid) continue;
          const i = Math.floor(p.angle_deg / width) % SECTORS;
          if (mins[i] === null || p.distance_mm < (mins[i] as number)) mins[i] = p.distance_mm;
        }
        setSectors(mins);
        if (mins.some((m) => m !== null && (m as number) < guardMm)) setTripped(true);
      } catch {
        /* keep watching */
      }
    }, 2500);
    return () => window.clearInterval(t);
  }, [watching, tripped, guardMm]);

  const estop = () => {
    // Honest E-STOP: halts OUR loops immediately and latches the guard.
    // Motion authority lives in the companion (yahboom-mcp) — this page
    // never pretends to brake the robot, it stops feeding it reasons to move.
    setWatching(false);
    setTripped(true);
  };

  return (
    <div data-testid="raspbots-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Raspbot Link — LiDAR riding shotgun</h1>
      <p className="max-w-3xl text-sm text-zinc-300">
        YDLIDAR on the mast, scan plane horizontal; lidar-mcp on the Raspberry Pi, yahboom-mcp
        driving. Probes are one-hop and fail-soft: a dead robot degrades this page, never the sensor
        core.
      </p>
      {error && <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">{error}</div>}
      <div className="grid gap-3 md:grid-cols-2">
        {companions.map((c) => {
          const p = probe[c.id];
          return (
            <div
              key={c.id}
              data-testid={`companion-${c.id}`}
              className="rounded border border-zinc-800 bg-zinc-900 p-3 text-sm"
            >
              <div className="flex items-center justify-between">
                <b>{c.label}</b>
                {c.status === "planned" ? (
                  <span className="rounded bg-zinc-800 px-2 py-0.5 text-sm text-zinc-300">
                    Planned — Nori A3 lands later
                  </span>
                ) : (
                  <span
                    className={`rounded px-2 py-0.5 ${p?.online ? "bg-emerald-900 text-emerald-200" : "bg-red-950 text-red-200"}`}
                  >
                    {p ? (p.online ? `online · ${p.latency_ms} ms` : "unreachable") : "probing…"}
                  </span>
                )}
              </div>
              <div className="mt-1 text-zinc-300">Mount: {c.mount}</div>
              <div className="mt-1 flex gap-2">
                {c.status === "live" && (
                  <>
                    <button
                      onClick={() => probeOne(c.id)}
                      className="rounded bg-zinc-800 px-2 py-0.5 hover:bg-zinc-700"
                    >
                      Re-probe
                    </button>
                    <a
                      href={c.dashboard_url}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded bg-zinc-800 px-2 py-0.5 text-cyan-200 hover:bg-zinc-700"
                    >
                      Open {c.repo}
                    </a>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <div className="rounded border border-zinc-800 bg-zinc-900 p-3">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="font-semibold">Obstacle guard</h2>
          <label className="text-sm text-zinc-300">
            trip (mm)
            <input
              type="number"
              value={guardMm}
              onChange={(e) => setGuardMm(Number(e.target.value))}
              className="ml-2 w-24 px-1"
            />
          </label>
          {!watching && !tripped && (
            <button
              data-testid="guard-start"
              onClick={() => {
                setTripped(false);
                setWatching(true);
              }}
              className="rounded bg-cyan-700 px-3 py-1 text-sm hover:bg-cyan-600"
            >
              Start guard
            </button>
          )}
          <button
            data-testid="guard-estop"
            onClick={estop}
            className="rounded bg-red-700 px-4 py-1 text-sm font-bold hover:bg-red-600"
          >
            E-STOP (halt local loops)
          </button>
          {tripped && (
            <span className="rounded bg-red-950 px-2 py-1 text-sm text-red-200">
              GUARD TRIPPED — local loops halted. Motion stop itself is yahboom-mcp's job; this page
              never brakes the robot.
            </span>
          )}
        </div>
        <div className="mt-3 flex gap-1" data-testid="guard-sectors">
          {sectors.map((m, i) => {
            const danger = m !== null && m < guardMm;
            return (
              <div
                key={i}
                title={`sector ${i * 45}°: ${m === null ? "no return" : `${m.toFixed(0)} mm`}`}
                className={`h-10 flex-1 rounded ${m === null ? "bg-zinc-800" : danger ? "bg-red-600" : "bg-emerald-800"}`}
              />
            );
          })}
          {sectors.length === 0 && (
            <div className="text-sm text-zinc-400">
              Start the guard to fill the 8 sector minima.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
