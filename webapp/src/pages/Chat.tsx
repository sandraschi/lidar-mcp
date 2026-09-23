import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useLlm } from "../store/llm";
import { useAsync } from "./Console";

interface Msg {
  role: string;
  content: string;
}

const PERSONALITIES: { name: string; prompt: string }[] = [
  {
    name: "Surveyor",
    prompt:
      "You are a LiDAR surveyor. Narrate scans in plain language: closest object, room shape, what changed.",
  },
  {
    name: "Robotics",
    prompt:
      "You are a robotics engineer. Interpret point clouds for obstacle avoidance and mapping decisions.",
  },
  {
    name: "Teacher",
    prompt:
      "You explain LiDAR simply: time-of-flight, angles, quality values, why glass is invisible.",
  },
  {
    name: "Tinkerer",
    prompt: "You suggest experiments: PTZ mounts, multi-pose mapping, sensor fusion on a budget.",
  },
  { name: "Custom", prompt: "" },
];

const EXAMPLES = [
  "What does a single 360° scan tell you about my room?",
  "Why do glass windows return quality 0?",
  "How do I mount this on a Raspbot mast?",
  "Explain the PTZ vertical-fan 3D hack.",
  "My scan shows 200 valid of 600 points — is that normal?",
  "How should I fuse scans from three poses?",
];

function loadHistory(): Msg[] {
  try {
    return JSON.parse(localStorage.getItem("lidar_chat") ?? "[]");
  } catch {
    return [];
  }
}

export default function Chat() {
  const llm = useLlm();
  const skills = useAsync(() =>
    api.skills().then((r) => r.data.skills.map((s) => s.markdown).join("\n")),
  );
  const [messages, setMessages] = useState<Msg[]>(loadHistory);
  const [input, setInput] = useState("");
  const [persona, setPersona] = useState(PERSONALITIES[0].name);
  const [custom, setCustom] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    llm.refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    localStorage.setItem("lidar_chat", JSON.stringify(messages.slice(-100)));
  }, [messages]);

  const personaPrompt =
    persona === "Custom" ? custom : (PERSONALITIES.find((p) => p.name === persona)?.prompt ?? "");

  const send = async (text: string) => {
    if (!text.trim() || busy) return;
    const next = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const system = `${skills.data ?? ""}\n${personaPrompt}`.trim();
      const resp = await fetch("/api/llm/chat/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          provider: llm.selectedProvider,
          model: llm.selectedModel,
          messages: [{ role: "system", content: system }, ...next],
        }),
      });
      const reader = resp.body?.getReader();
      const decoder = new TextDecoder();
      let reply = "";
      setMessages([...next, { role: "assistant", content: "" }]);
      if (reader) {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          for (const line of decoder.decode(value).split("\n")) {
            if (!line.startsWith("data:")) continue;
            const data = line.slice(5).trim();
            if (data === "[DONE]") break;
            try {
              const obj = JSON.parse(data);
              if (obj.delta) {
                reply += obj.delta as string;
                setMessages([...next, { role: "assistant", content: reply }]);
              }
            } catch {
              /* partial chunk */
            }
          }
        }
      }
    } catch (e) {
      setMessages([...next, { role: "assistant", content: `Error: ${String(e)}` }]);
    } finally {
      setBusy(false);
    }
  };

  const canChat = !!llm.selectedProvider && !!llm.selectedModel;

  return (
    <div data-testid="chat-page" className="flex h-full flex-col space-y-3">
      <h1 className="text-xl font-semibold">Chat — skill-first LiDAR assistant</h1>
      <div
        data-testid="chat-controls"
        className="flex flex-wrap items-center gap-3 rounded border border-zinc-800 bg-zinc-900 p-2 text-sm"
      >
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${canChat ? "bg-emerald-400" : "bg-amber-400"}`}
          title={canChat ? "LLM ready" : "No LLM selected"}
        />
        <span className="text-zinc-300">
          {canChat
            ? `${llm.selectedProvider} / ${llm.selectedModel}`
            : "No local LLM detected. Start Ollama or LM Studio."}
        </span>
        <label className="text-zinc-300">
          Personality
          <select
            data-testid="personality-select"
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
            className="ml-2 px-2 py-0.5"
          >
            {PERSONALITIES.map((p) => (
              <option key={p.name}>{p.name}</option>
            ))}
          </select>
        </label>
        {persona === "Custom" && (
          <input
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            placeholder="custom system prompt"
            className="rounded px-2 py-0.5 text-sm"
          />
        )}
        <button
          data-testid="chat-export"
          disabled={messages.length === 0}
          onClick={() => {
            const blob = new Blob([messages.map((m) => `${m.role}: ${m.content}`).join("\n\n")], {
              type: "text/plain",
            });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "lidar-chat.txt";
            a.click();
          }}
          className="rounded bg-zinc-800 px-2 py-0.5 hover:bg-zinc-700 disabled:opacity-50"
        >
          Export
        </button>
        <button
          data-testid="chat-clear"
          disabled={messages.length === 0}
          onClick={() => {
            setMessages([]);
            localStorage.removeItem("lidar_chat");
          }}
          className="rounded bg-zinc-800 px-2 py-0.5 hover:bg-zinc-700 disabled:opacity-50"
        >
          Clear
        </button>
      </div>
      <div data-testid="example-prompts" className="flex flex-wrap gap-2">
        {EXAMPLES.map((e) => (
          <button
            key={e}
            onClick={() => send(e)}
            disabled={!canChat || busy}
            className="rounded bg-zinc-800 px-2 py-1 text-sm text-zinc-300 hover:bg-zinc-700 disabled:opacity-50"
          >
            {e}
          </button>
        ))}
      </div>
      <div
        data-testid="chat-messages"
        className="min-h-48 flex-1 space-y-2 overflow-y-auto rounded border border-zinc-800 bg-zinc-900 p-3"
      >
        {messages.length === 0 && (
          <div className="text-sm text-zinc-400">
            Ask about your scans, mounts, or mapping plans. History persists locally (100 cap).
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded p-2 text-sm ${m.role === "user" ? "bg-zinc-800" : "bg-zinc-900 text-zinc-200"}`}
          >
            <b className="text-zinc-400">{m.role}:</b> {m.content}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder={canChat ? "Ask…" : "Select a provider in Settings first"}
          disabled={!canChat}
          className="flex-1 rounded px-3 py-2 text-sm"
        />
        <button
          data-testid="chat-send"
          onClick={() => send(input)}
          disabled={!canChat || busy}
          className="rounded bg-cyan-700 px-4 py-2 text-sm hover:bg-cyan-600 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
