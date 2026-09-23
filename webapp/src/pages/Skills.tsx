import { useState } from "react";
import { api } from "../lib/api";
import { useAsync } from "./Console";

function renderMarkdown(md: string) {
  return md.split("\n").map((line, i) => {
    if (line.startsWith("## ")) return <h3 key={i} className="mt-3 font-semibold text-cyan-200">{line.slice(3)}</h3>;
    if (line.startsWith("# ")) return <h2 key={i} className="mt-3 text-lg font-bold">{line.slice(2)}</h2>;
    if (line.startsWith("- ") || line.startsWith("* ")) return <li key={i} className="ml-4 list-disc text-zinc-300">{line.slice(2)}</li>;
    if (line.startsWith("```")) return <hr key={i} className="my-2 border-zinc-800" />;
    if (!line.trim()) return <br key={i} />;
    return <p key={i} className="text-sm text-zinc-300">{line}</p>;
  });
}

export default function Skills() {
  const skills = useAsync(() => api.skills().then((r) => r.data.skills));
  const [sel, setSel] = useState(0);
  const list = skills.data ?? [];

  return (
    <div data-testid="skills-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Skills — how agents should use this server</h1>
      {skills.loading && <div className="text-sm text-zinc-300">Loading skills…</div>}
      {skills.error && <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">Failed: {skills.error}</div>}
      {list.length === 0 && !skills.loading && (
        <div className="rounded border border-zinc-800 p-6 text-sm text-zinc-300">No skills exposed.</div>
      )}
      <div className="flex gap-4">
        <div className="w-56 space-y-1">
          {list.map((s, i) => (
            <button
              key={s.name}
              onClick={() => setSel(i)}
              className={`block w-full rounded px-3 py-2 text-left text-sm ${i === sel ? "bg-zinc-800 text-cyan-200" : "text-zinc-300 hover:bg-zinc-800/60"}`}
            >
              {s.name} <span className="text-zinc-500">({s.source})</span>
            </button>
          ))}
        </div>
        {list[sel] && <div className="flex-1 rounded border border-zinc-800 bg-zinc-900 p-4">{renderMarkdown(list[sel].markdown)}</div>}
      </div>
    </div>
  );
}
