import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAsync } from "./Console";
import { useLlm } from "../store/llm";
import { useEffect } from "react";

export default function Dashboard() {
  const dash = useAsync(() => api.dashboard().then((r) => r.data.kpis));
  const onboard = useAsync(() => api.llmOnboarding().then((r) => r.data));
  const llm = useLlm();
  useEffect(() => {
    llm.refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <section className="rounded border border-zinc-800 bg-gradient-to-br from-zinc-900 to-zinc-950 p-6">
        <h1 className="text-2xl font-bold">Turn a $30 YDLIDAR into an AI-readable room.</h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-300">
          Scans, maps, and robot linkage for YDLIDAR USB sensors — live polar scope, pose-tagged mapper,
          Raspbot obstacle guard, and a $50 PTZ 3D rig. Plug the module in and start with the Console.
        </p>
        <div className="mt-4 flex gap-3">
          <Link data-testid="hero-cta" to="/console" className="rounded bg-cyan-700 px-4 py-2 text-sm font-semibold hover:bg-cyan-600">
            Open Console — test my module
          </Link>
          <Link to="/scope" className="rounded bg-zinc-800 px-4 py-2 text-sm hover:bg-zinc-700">
            Live scope
          </Link>
        </div>
        {onboard.data && !onboard.data.ready && (
          <Link
            data-testid="onboarding-cue"
            to="/settings"
            className="mt-4 block rounded border border-red-800 bg-red-950 p-3 text-sm text-red-100"
          >
            No usable LLM yet — set up a provider in Settings to unlock Chat. Local (Ollama/LM Studio) is free.
          </Link>
        )}
      </section>
      {dash.loading && <div className="text-sm text-zinc-300">Loading stats…</div>}
      {dash.error && <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">Stats failed: {dash.error}</div>}
      <section className="grid gap-3 md:grid-cols-4">
        {(dash.data ?? []).map((k) => (
          <div key={k.name} data-testid={`kpi-${k.name.toLowerCase().replace(/\s+/g, "-")}`} className="rounded border border-zinc-800 bg-zinc-900 p-4">
            <div className="text-sm text-zinc-400">{k.name}</div>
            <div className="text-2xl font-bold text-cyan-200">{k.value}</div>
            <div className="text-sm text-zinc-400">{k.hint}</div>
          </div>
        ))}
      </section>
      <section className="grid gap-3 md:grid-cols-3">
        {[
          { to: "/mapper", t: "Build a room map", d: "Capture scans at poses, stitch a global map." },
          { to: "/raspbots", t: "Link the Raspbot", d: "Yahboom companion probe + obstacle guard." },
          { to: "/diff", t: "Spot what moved", d: "A/B scan diff with per-sector deltas." },
        ].map((c) => (
          <Link key={c.to} to={c.to} className="rounded border border-zinc-800 bg-zinc-900 p-4 hover:border-cyan-700">
            <div className="font-semibold text-cyan-200">{c.t}</div>
            <div className="text-sm text-zinc-300">{c.d}</div>
          </Link>
        ))}
      </section>
    </div>
  );
}
