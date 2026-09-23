import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAsync } from "./Console";

export default function Library() {
  const [preview, setPreview] = useState("");
  const [previewId, setPreviewId] = useState("");
  const scans = useAsync(() => api.scans().then((r) => r.data.scans));

  const showMap = async (id: string) => {
    try {
      const r = await api.map({ source: id, format: "svg", grid_size: 40 });
      if (r.success && r.data.svg) {
        setPreview(r.data.svg);
        setPreviewId(id);
      }
    } catch {
      setPreview("");
    }
  };

  return (
    <div data-testid="library-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Scan Library — saved sweeps</h1>
      {scans.loading && <div className="text-sm text-zinc-300">Loading saved scans…</div>}
      {scans.error && (
        <div className="rounded border border-red-800 bg-red-950 p-3 text-sm">
          Failed: {scans.error}
        </div>
      )}
      {scans.data && scans.data.length === 0 && (
        <div className="rounded border border-zinc-800 p-6 text-sm text-zinc-300">
          No saved scans yet. Capture one from the{" "}
          <Link to="/console" className="text-cyan-300">
            Console
          </Link>{" "}
          with a note.
        </div>
      )}
      <div className="flex flex-wrap gap-4">
        <div className="min-w-72 flex-1 space-y-2">
          {(scans.data ?? []).map((s) => (
            <button
              key={s.scan_id}
              onClick={() => showMap(s.scan_id)}
              className="block w-full rounded border border-zinc-800 bg-zinc-900 p-3 text-left text-sm hover:border-cyan-700"
            >
              <div className="font-mono text-cyan-200">{s.scan_id}</div>
              <div className="text-zinc-300">
                {s.note || "no note"} · {s.valid_count}/{s.point_count} valid
              </div>
              <div className="text-zinc-400">{s.saved_at}</div>
            </button>
          ))}
        </div>
        {preview && (
          <div className="flex-1">
            <div className="mb-2 text-sm text-zinc-300">
              {previewId} — pick two scans and open{" "}
              <Link to="/diff" className="text-cyan-300">
                Diff Lab
              </Link>{" "}
              to compare.
            </div>
            {/* biome-ignore lint/security/noDangerouslySetInnerHtml: SVG rendered by our own backend from scan data */}
            <div dangerouslySetInnerHTML={{ __html: preview }} className="max-w-xl" />
          </div>
        )}
      </div>
    </div>
  );
}
