import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useLlm } from "../store/llm";

export default function Settings() {
  const llm = useLlm();
  const [keys, setKeys] = useState<Record<string, string>>({ openai: "", anthropic: "" });
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [msg, setMsg] = useState("");
  const [job, setJob] = useState("");

  useEffect(() => {
    llm.refresh();
    api.llmKeys().then((r) => setFlags(r.data.keys_configured)).catch(() => setFlags({}));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const saveKey = async (id: string) => {
    try {
      const r = await api.llmSetKey(id, keys[id]);
      setFlags(r.data.keys_configured);
      setKeys((k) => ({ ...k, [id]: "" }));
      setMsg(r.message);
      llm.refresh();
    } catch (e) {
      setMsg(String(e));
    }
  };

  const clearKey = async (id: string) => {
    await api.llmClearKey(id);
    const r = await api.llmKeys();
    setFlags(r.data.keys_configured);
    llm.refresh();
  };

  const installOllama = async () => {
    const r = await fetch("/api/llm/install", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ engine: "ollama" }) }).then((x) => x.json());
    if (r.success) {
      setJob(r.data.job_id);
      const t = window.setInterval(async () => {
        const s = await fetch(`/api/llm/install/status?job_id=${r.data.job_id}`).then((x) => x.json());
        setMsg(`Install: ${s.data.status} — ${s.data.engine}`);
        if (s.data.status === "done" || s.data.status === "failed") {
          window.clearInterval(t);
          llm.refresh();
        }
      }, 3000);
    }
  };

  return (
    <div data-testid="settings-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Settings — backend & intelligence</h1>
      {msg && <div className="rounded border border-zinc-800 bg-zinc-900 p-2 text-sm">{msg}</div>}
      <section className="rounded border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="font-semibold">Active pair</h2>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
          <label className="text-zinc-300">Provider
            <select data-testid="llm-provider-select" value={llm.selectedProvider} onChange={(e) => llm.selectProvider(e.target.value)} className="ml-2 px-2 py-1">
              {llm.selectedProvider === "" && <option value="">No local LLM detected</option>}
              {llm.providers.filter((p) => (p.kind === "local" ? p.detected : p.configured)).map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </label>
          <label className="text-zinc-300">Model
            <select data-testid="llm-model-select" value={llm.selectedModel} onChange={(e) => llm.selectModel(e.target.value)} className="ml-2 px-2 py-1">
              {llm.availableModels.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </label>
          {llm.gpus.length > 1 && (
            <label className="text-zinc-300">GPU
              <select data-testid="llm-gpu-select" value={llm.targetGpuIndex} onChange={(e) => llm.selectGpu(Number(e.target.value))} className="ml-2 px-2 py-1">
                {llm.gpus.map((g) => <option key={g.index} value={g.index}>GPU {g.index} — {g.name} ({(g.vramMb / 1024).toFixed(0)} GB)</option>)}
              </select>
            </label>
          )}
        </div>
      </section>
      <section className="grid gap-3 md:grid-cols-2">
        {llm.providers.map((p) => (
          <div key={p.id} data-testid={`llm-provider-card-${p.id}`} className="rounded border border-zinc-800 bg-zinc-900 p-4 text-sm">
            <div className="flex items-center justify-between">
              <b>{p.label}</b>
              <span className={`rounded px-2 py-0.5 ${p.kind === "local" ? "bg-emerald-900 text-emerald-200" : "bg-amber-900 text-amber-200"}`}>
                {p.kind === "local" ? "Local / free" : "Cloud / paid"}
              </span>
            </div>
            <div className="mt-1 text-zinc-300">
              {p.kind === "local"
                ? (llm.providerStatus[p.id] === "detected" ? `Detected at ${p.base_url}` : llm.providerStatus[p.id] === "probing" ? "Probing…" : "Not found")
                : (flags[p.id] ? "Key configured" : "No key")}
            </div>
            {p.kind === "cloud" && (
              <div className="mt-2 flex gap-2">
                <input
                  data-testid={`llm-key-${p.id}`}
                  type="password"
                  value={keys[p.id] ?? ""}
                  onChange={(e) => setKeys((k) => ({ ...k, [p.id]: e.target.value }))}
                  placeholder={`${p.key_env}…`}
                  className="flex-1 rounded px-2 py-1 text-sm"
                />
                <button data-testid={`llm-test-${p.id}`} onClick={() => saveKey(p.id)} className="rounded bg-zinc-800 px-2 py-1 hover:bg-zinc-700">Save</button>
                <button onClick={() => clearKey(p.id)} className="rounded bg-zinc-800 px-2 py-1 hover:bg-zinc-700">Clear</button>
              </div>
            )}
          </div>
        ))}
      </section>
      <section data-testid="llm-onboarding" className="rounded border border-zinc-800 bg-zinc-900 p-4 text-sm">
        <h2 className="font-semibold">First run?</h2>
        <p className="mt-1 text-zinc-300">Free path: install Ollama, pull a small model, come back. Nothing to paste, nothing to pay.</p>
        <button onClick={installOllama} className="mt-2 rounded bg-cyan-700 px-3 py-1 hover:bg-cyan-600">Install Ollama (winget)</button>
        {job && <div className="mt-1 font-mono text-zinc-400">job {job}</div>}
      </section>
    </div>
  );
}
