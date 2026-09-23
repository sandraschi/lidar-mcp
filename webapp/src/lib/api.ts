// Typed REST client for the lidar-mcp web backend (11217).
// Same-origin in prod (backend serves dist/), Vite-proxied in dev.
// Chat NEVER touches providers directly — always POST /api/llm/chat.

export interface ScanPoint {
  angle_deg: number;
  distance_mm: number;
  quality: number;
  is_valid: boolean;
  is_sync: boolean;
}

export interface ScanData {
  point_count: number;
  valid_count: number;
  duration_ms: number;
  points: ScanPoint[];
}

export interface ApiResult<T> {
  success: boolean;
  message: string;
  data: T;
}

async function req<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  const resp = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as ApiResult<T>;
}

export const api = {
  health: () => fetch("/api/health").then((r) => r.json()),
  status: () => fetch("/api/status").then((r) => r.json()),
  dashboard: () =>
    req<{ kpis: { name: string; value: string | number; hint: string }[] }>("/api/dashboard"),
  ports: () => req<{ ports: string[] }>("/api/ports"),
  tools: () =>
    req<{
      tools: {
        name: string;
        summary: string;
        docstring: string;
        parameters: { name: string; default: string | null }[];
        portmanteau: boolean;
      }[];
    }>("/api/tools"),
  skills: () =>
    req<{ skills: { name: string; source: string; markdown: string }[] }>("/api/skills"),
  logs: () =>
    req<{
      logs: { ts: string; level: string; logger: string; message: string }[];
    }>("/api/logs"),
  scan: (timeout_s = 3.0, port = "") =>
    req<ScanData>("/api/scan", {
      method: "POST",
      body: JSON.stringify({ timeout_s, port }),
    }),
  scans: () =>
    req<{
      scans: {
        scan_id: string;
        saved_at: string;
        note: string;
        point_count: number;
        valid_count: number;
      }[];
    }>("/api/scans"),
  saveScan: (note: string, timeout_s = 3.0, port = "") =>
    req<ScanData & { scan_id: string; saved_at: string }>("/api/scans/save", {
      method: "POST",
      body: JSON.stringify({ note, timeout_s, port }),
    }),
  map: (body: {
    source: string;
    format: string;
    grid_size?: number;
    range_max_mm?: number;
    timeout_s?: number;
  }) =>
    req<{
      svg?: string;
      grid?: {
        grid_size: number;
        cell_mm: number;
        range_max_mm: number;
        occupied_count: number;
        rows: string[];
      };
      point_count: number;
      valid_count: number;
      range_max_mm: number;
    }>("/api/map", {
      method: "POST",
      body: JSON.stringify({
        grid_size: 100,
        range_max_mm: 0,
        timeout_s: 3.0,
        ...body,
      }),
    }),
  diff: (body: { scan_a: string; scan_b: string; sector_deg?: number; tolerance_mm?: number }) =>
    req<{
      scan_a: string;
      scan_b: string;
      sector_deg: number;
      tolerance_mm: number;
      changed_count: number;
      changed: {
        sector_deg: number;
        scan_a_mm: number | null;
        scan_b_mm: number | null;
        delta_mm: number | null;
      }[];
    }>("/api/diff", { method: "POST", body: JSON.stringify(body) }),
  companions: () =>
    req<{
      companions: {
        id: string;
        label: string;
        repo: string;
        health_url: string;
        dashboard_url: string;
        mount: string;
        status: string;
      }[];
    }>("/api/companions"),
  companion: (id: string) =>
    req<{
      online: boolean;
      planned?: boolean;
      latency_ms: number | null;
      detail: unknown;
    }>(`/api/companions/${id}`),
  llmDiscover: () => req<{ providers: LlmProvider[] }>("/api/llm/discover"),
  llmProviders: () => req<{ providers: LlmProvider[] }>("/api/llm/providers"),
  llmModels: (provider: string) =>
    req<{ models: string[]; source: string }>(
      `/api/llm/models?provider=${encodeURIComponent(provider)}`,
    ),
  llmGpus: () => req<{ gpus: { index: number; name: string; vramMb: number }[] }>("/api/llm/gpus"),
  llmOnboarding: () =>
    req<{
      ready: boolean;
      recommended_path: string;
      facts: string[];
      locals: string[];
      clouds_keyed: string[];
    }>("/api/llm/onboarding"),
  llmChat: (provider: string, model: string, messages: { role: string; content: string }[]) =>
    req<{ reply: string }>("/api/llm/chat", {
      method: "POST",
      body: JSON.stringify({ provider, model, messages }),
    }),
  llmKeys: () => req<{ keys_configured: Record<string, boolean> }>("/api/settings/llm"),
  llmSetKey: (provider: string, api_key: string) =>
    req<{ keys_configured: Record<string, boolean> }>("/api/settings/llm", {
      method: "POST",
      body: JSON.stringify({ provider, api_key }),
    }),
  llmClearKey: (provider: string) =>
    fetch(`/api/settings/llm/key?provider=${encodeURIComponent(provider)}`, {
      method: "DELETE",
    }).then((r) => r.json()),
};

export interface LlmProvider {
  id: string;
  label: string;
  kind: "local" | "cloud";
  base_url: string;
  needs_key: boolean;
  key_env: string;
  configured: boolean;
  detected?: boolean;
  models?: string[];
  loaded?: string[];
}

// Backend health with exponential backoff (1s, 2s, 4s, 8s, 16s cap).
export async function waitForBackend(
  onState: (ok: boolean, attempt: number) => void,
): Promise<void> {
  const delays = [1000, 2000, 4000, 8000, 16000];
  for (let i = 0; i < delays.length; i++) {
    try {
      const h = await api.health();
      if (h.status === "ok") {
        onState(true, i);
        return;
      }
    } catch {
      onState(false, i);
    }
    await new Promise((r) => setTimeout(r, delays[i]));
  }
  onState(false, delays.length);
}
