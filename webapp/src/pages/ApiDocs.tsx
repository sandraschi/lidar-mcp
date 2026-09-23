import { useState } from "react";

const ENDPOINTS = [
  "GET /api/health",
  "GET /api/status",
  "GET /api/dashboard",
  "GET /api/ports",
  "GET /api/tools",
  "GET /api/skills",
  "GET /api/logs",
  "POST /api/scan",
  "GET /api/scans",
  "GET /api/scans/{id}",
  "POST /api/scans/save",
  "POST /api/map",
  "POST /api/diff",
  "GET /api/llm/providers",
  "GET /api/llm/models",
  "POST /api/llm/chat",
  "GET /api/companions",
  "POST /api/shutdown",
];

export default function ApiDocs() {
  const [view, setView] = useState<"swagger" | "redoc">("swagger");
  const src = view === "swagger" ? "/docs" : "/redoc";
  return (
    <div data-testid="api-docs-page" className="flex h-full flex-col space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">API Docs — live backend reference</h1>
        <button
          data-testid="docs-swagger"
          onClick={() => setView("swagger")}
          className={`rounded px-3 py-1 text-sm ${view === "swagger" ? "bg-cyan-700" : "bg-zinc-800 hover:bg-zinc-700"}`}
        >
          Swagger
        </button>
        <button
          data-testid="docs-redoc"
          onClick={() => setView("redoc")}
          className={`rounded px-3 py-1 text-sm ${view === "redoc" ? "bg-cyan-700" : "bg-zinc-800 hover:bg-zinc-700"}`}
        >
          ReDoc
        </button>
        <a
          data-testid="docs-open-browser"
          href="http://127.0.0.1:11217/docs"
          target="_blank"
          rel="noreferrer"
          className="rounded bg-zinc-800 px-3 py-1 text-sm text-cyan-200 hover:bg-zinc-700"
        >
          Open in browser
        </a>
      </div>
      <div className="flex gap-2 overflow-x-auto rounded border border-zinc-800 bg-zinc-900 p-2 text-sm">
        {ENDPOINTS.map((e) => (
          <code
            key={e}
            className="whitespace-nowrap rounded bg-zinc-800 px-2 py-0.5 font-mono text-cyan-200"
          >
            {e}
          </code>
        ))}
      </div>
      <iframe
        title="API docs"
        src={src}
        className="min-h-96 flex-1 rounded border border-zinc-800 bg-zinc-950"
      />
    </div>
  );
}
