import { create } from "zustand";
import { api, type LlmProvider } from "../lib/api";

interface LlmState {
  providers: LlmProvider[];
  providerStatus: Record<string, "probing" | "detected" | "not_found">;
  selectedProvider: string;
  availableModels: string[];
  selectedModel: string;
  gpus: { index: number; name: string; vramMb: number }[];
  targetGpuIndex: number;
  ready: boolean;
  refresh: () => Promise<void>;
  selectProvider: (id: string) => Promise<void>;
  selectModel: (model: string) => void;
  selectGpu: (index: number) => void;
}

const storedProvider = localStorage.getItem("llm_provider") ?? "";
const storedModel = localStorage.getItem("llm_model") ?? "";
const storedGpu = Number(localStorage.getItem("llm_gpu") ?? "-1");

export const useLlm = create<LlmState>((set, get) => ({
  providers: [],
  providerStatus: {},
  selectedProvider: storedProvider,
  availableModels: [],
  selectedModel: storedModel,
  gpus: [],
  targetGpuIndex: storedGpu,
  ready: false,
  refresh: async () => {
    const status: Record<string, "probing" | "detected" | "not_found"> = {};
    for (const id of ["ollama", "lmstudio", "vllm"]) status[id] = "probing";
    set({ providerStatus: status });
    let providers: LlmProvider[] = [];
    try {
      providers = (await api.llmProviders()).data.providers;
    } catch {
      providers = [];
    }
    const next: typeof status = {};
    for (const p of providers) {
      if (p.kind === "local") next[p.id] = p.detected ? "detected" : "not_found";
    }
    set({ providers, providerStatus: { ...get().providerStatus, ...next } });
    // GPU placement: default to the secondary card on multi-GPU machines.
    let gpus: LlmState["gpus"] = [];
    try {
      gpus = (await api.llmGpus()).data.gpus;
    } catch {
      gpus = [];
    }
    let target = get().targetGpuIndex;
    if (gpus.length > 1 && !gpus.some((g) => g.index === target)) {
      target = Math.max(...gpus.map((g) => g.index));
    } else if (gpus.length === 1) {
      target = gpus[0].index;
    }
    localStorage.setItem("llm_gpu", String(target));
    // Provider default: saved still configured/detected wins, else first usable.
    const usable = providers.filter((p) => (p.kind === "local" ? p.detected : p.configured));
    let sel = get().selectedProvider;
    if (!usable.some((p) => p.id === sel)) sel = usable[0]?.id ?? "";
    localStorage.setItem("llm_provider", sel);
    set({ gpus, targetGpuIndex: target, selectedProvider: sel, ready: true });
    if (sel) await get().selectProvider(sel);
  },
  selectProvider: async (id: string) => {
    localStorage.setItem("llm_provider", id);
    set({ selectedProvider: id, availableModels: [], selectedModel: "" });
    try {
      const models = (await api.llmModels(id)).data.models;
      const saved = localStorage.getItem("llm_model") ?? "";
      const sel = models.includes(saved) ? saved : (models[0] ?? "");
      localStorage.setItem("llm_model", sel);
      set({ availableModels: models, selectedModel: sel });
    } catch {
      set({ availableModels: [], selectedModel: "" });
    }
  },
  selectModel: (model: string) => {
    localStorage.setItem("llm_model", model);
    set({ selectedModel: model });
  },
  selectGpu: (index: number) => {
    localStorage.setItem("llm_gpu", String(index));
    set({ targetGpuIndex: index });
  },
}));
