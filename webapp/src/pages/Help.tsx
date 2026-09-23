import { useState } from "react";

const TABS: { id: string; title: string; body: string[] }[] = [
  {
    id: "start",
    title: "Getting started",
    body: [
      "1. Plug the YDLIDAR into USB (direct port, no hub for first test).",
      "2. Open Console, pick the serial port (or leave auto = LIDAR_PORT).",
      "3. Status for firmware/health, Scan once for a 360° sweep.",
      "4. Save interesting scans to the Library, compare pairs in Diff Lab.",
    ],
  },
  {
    id: "hardware",
    title: "Wrappee hardware",
    body: [
      "Supported: X2, X4, G1, G4, G6, S2, S4, S2B, S4B, T1 (SDK2 protocol).",
      "USB chips: CP210x (X series) / CH340 (G/S series) — inbox drivers.",
      "Power: ~300-400 mA. Short shielded cable, max 2 m.",
      "785 nm IR: glass and mirrors return nothing (quality 0) — physics, not a bug.",
      "Dark surfaces halve the range. Sunlight adds IR noise outdoors.",
    ],
  },
  {
    id: "api",
    title: "API & ports",
    body: [
      "MCP SSE 11075 (legacy) · stdio for Claude Desktop.",
      "Web API 11217 · frontend dev 11218. Swagger at /docs.",
      "Pi deploy: run the API on the Raspberry Pi, open the UI from your laptop over Tailscale/LAN.",
      "POST /api/shutdown schedules an orderly exit (fleet launcher contract).",
    ],
  },
  {
    id: "errors",
    title: "Error fix",
    body: [
      "'No LiDAR port' → set LIDAR_PORT or pick the port in Console.",
      "Timeouts / CRC errors → cable power, or another app holds the COM port.",
      "All-zero distances → motor stalled or protective film still on the window.",
      "Companion unreachable → start yahboom-mcp (10892) first; pages degrade, never crash.",
    ],
  },
  {
    id: "faq",
    title: "FAQ",
    body: [
      "Mapper drift? Poses are trusted blindly — measure them, overlap scans 30-50%.",
      "SLAM? No. Pose-tagged stitching. Labelled honestly on the Mapper page.",
      "Nori A3 support? Planned companion, not wired yet (see Raspbot Link).",
      "Keys: cloud LLM keys live in data/llm_keys.json (0600) or env — never in the browser.",
    ],
  },
];

export default function Help() {
  const [tab, setTab] = useState("start");
  const active = TABS.find((t) => t.id === tab)!;
  return (
    <div data-testid="help-page" className="space-y-4">
      <h1 className="text-xl font-semibold">Help</h1>
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded px-3 py-1 text-sm ${t.id === tab ? "bg-cyan-700" : "bg-zinc-800 hover:bg-zinc-700"}`}
          >
            {t.title}
          </button>
        ))}
      </div>
      <div className="rounded border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="font-semibold text-cyan-200">{active.title}</h2>
        <ul className="mt-2 space-y-1 text-sm text-zinc-300">
          {active.body.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      </div>
      <div className="text-sm text-zinc-400">
        Full docs: README · INSTALL · docs/CONFIGURATION · docs/TOOLS · docs/TROUBLESHOOTING · docs/ONBOARDING · llms-full.txt
      </div>
    </div>
  );
}
