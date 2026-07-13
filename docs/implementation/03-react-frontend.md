# Phase 3 — React frontend

This phase builds an accessible React/Vite client for the read-only Ops Agent. It sends the canonical request:

```json
{"message":"Who has LT-100?","thread_id":"c6cbdc9b-cf80-41bd-87f7-454a8478c0a6"}
```

and accepts only:

```json
{"answer":"LT-100 is assigned to Maya.","thread_id":"c6cbdc9b-cf80-41bd-87f7-454a8478c0a6","tool_rounds":2,"soft_limit_reached":false}
```

The transcript contains only user messages and final `answer` values. Tool calls, tool results, intermediate model messages, prompts, and chain-of-thought never enter frontend state.

## Target tree

```text
frontend/
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── eslint.config.js
├── index.html
├── nginx.conf
├── package.json
├── package-lock.json                 # generated; do not type
├── tsconfig.app.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
└── src/
    ├── App.test.tsx
    ├── App.tsx
    ├── api.test.ts
    ├── api.ts
    ├── main.tsx
    ├── styles.css
    ├── thread.test.ts
    ├── thread.ts
    ├── vite-env.d.ts
    ├── components/
    │   ├── ChatComposer.test.tsx
    │   ├── ChatComposer.tsx
    │   └── MessageList.tsx
    └── test/setup.ts
```

## Tooling and entry files

### `frontend/package.json`

```json
{
  "name": "ops-agent-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": {"node": ">=22.12"},
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 5173",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 0.0.0.0 --port 5173",
    "typecheck": "tsc -b --pretty false",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.30.1",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.3.0",
    "@testing-library/user-event": "^14.6.1",
    "@types/node": "^22.15.32",
    "@types/react": "^19.1.8",
    "@types/react-dom": "^19.1.6",
    "@vitejs/plugin-react": "^4.6.0",
    "eslint": "^9.30.1",
    "eslint-plugin-react-hooks": "^5.2.0",
    "eslint-plugin-react-refresh": "^0.4.20",
    "globals": "^16.3.0",
    "jsdom": "^26.1.0",
    "typescript": "~5.8.3",
    "typescript-eslint": "^8.35.1",
    "vite": "^7.0.4",
    "vitest": "^3.2.4"
  }
}
```

React is the only runtime library. Vitest shares Vite resolution and Testing Library verifies DOM behavior. Run `cd frontend && npm install`; npm generates `package-lock.json`. Commit it with `package.json` so local, CI, and Docker `npm ci` installs agree. Never hand-write or paste a fabricated lockfile.

### `frontend/tsconfig.json`

```json
{"files":[],"references":[{"path":"./tsconfig.app.json"},{"path":"./tsconfig.node.json"}]}
```

### `frontend/tsconfig.app.json`

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/app.tsbuildinfo",
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,
    "skipLibCheck": true,
    "composite": true,
    "types": ["vite/client", "vitest/globals"]
  },
  "include": ["src"]
}
```

### `frontend/tsconfig.node.json`

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/node.tsbuildinfo",
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "skipLibCheck": true,
    "composite": true,
    "types": ["node"]
  },
  "include": ["vite.config.ts"]
}
```

Separate projects prevent browser code from accidentally using Node globals. Strict checking catches state and contract mistakes; Vite, not TypeScript, emits browser assets.

### `frontend/vite.config.ts`

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    restoreMocks: true,
  },
});
```

### `frontend/eslint.config.js`

```js
import js from "@eslint/js";
import globals from "globals";
import hooks from "eslint-plugin-react-hooks";
import refresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "coverage"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: {...globals.browser, ...globals.node},
    },
    plugins: {"react-hooks": hooks, "react-refresh": refresh},
    rules: {
      ...hooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", {allowConstantExport: true}],
    },
  },
);
```

### `frontend/index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="Read-only asset operations assistant." />
    <meta name="theme-color" content="#102a43" />
    <title>Ops Agent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### `frontend/.gitignore`

```gitignore
node_modules/
dist/
coverage/
*.local
.env.local
.env.*.local
```

## Vite environment

### `frontend/.env.example`

```dotenv
# Public browser-visible URL, embedded when Vite builds.
VITE_AGENT_URL=http://localhost:8001
```

### `frontend/src/vite-env.d.ts`

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AGENT_URL: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

Copy the example to `.env.local` for development. `VITE_` values are public and must contain no secrets. Vite embeds this value during `npm run build`; changing the runtime environment of an existing Nginx container does not alter its bundle.

The static JavaScript executes in the user's browser. For local Compose, `http://localhost:8001` reaches the agent's published host port. `http://agent:8001` is resolvable by other Docker containers, not normally by the host browser, so never bake that Docker service hostname into this bundle. For remote use, build with the public HTTPS origin or a browser-visible same-origin path. The agent must allow `http://localhost:5173` through CORS.

## Typed, runtime-validated API client

### `frontend/src/api.ts`

```ts
export interface ChatRequest { message: string; thread_id: string }
export interface ChatResponse {
  answer: string;
  thread_id: string;
  tool_rounds: number;
  soft_limit_reached: boolean;
}

export class ChatApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ChatApiError";
  }
}

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const isUuid = (v: unknown): v is string =>
  typeof v === "string" &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v);

function parseResponse(value: unknown): ChatResponse {
  if (
    !isRecord(value) ||
    typeof value.answer !== "string" ||
    !value.answer.trim() ||
    !isUuid(value.thread_id) ||
    !Number.isInteger(value.tool_rounds) ||
    (value.tool_rounds as number) < 0 ||
    typeof value.soft_limit_reached !== "boolean"
  ) throw new ChatApiError("The agent returned an invalid response.");
  return value as unknown as ChatResponse;
}

function assertRequest(request: ChatRequest) {
  if (typeof request.message !== "string" || !request.message.trim())
    throw new ChatApiError("A non-empty message is required.");
  if (!isUuid(request.thread_id))
    throw new ChatApiError("A valid thread ID is required.");
}

function baseUrl() {
  const value = import.meta.env.VITE_AGENT_URL?.trim().replace(/\/+$/, "");
  if (!value) throw new ChatApiError("VITE_AGENT_URL is not configured.");
  return value;
}

async function detail(response: Response) {
  if (!(response.headers.get("content-type") ?? "").includes("application/json"))
    return undefined;
  try {
    const body: unknown = await response.json();
    return isRecord(body) && typeof body.detail === "string" ? body.detail : undefined;
  } catch {
    return undefined;
  }
}

export async function postChat(
  request: ChatRequest,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  assertRequest(request);
  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/chat`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(request),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ChatApiError("Could not reach the agent. Check its status and CORS.");
  }
  if (!response.ok) {
    const reason = await detail(response);
    throw new ChatApiError(
      `Agent request failed (${response.status}).${reason ? ` ${reason}` : ""}`,
      response.status,
    );
  }
  let body: unknown;
  try { body = await response.json(); }
  catch { throw new ChatApiError("The agent returned invalid JSON.", response.status); }
  const parsed = parseResponse(body);
  if (parsed.thread_id !== request.thread_id)
    throw new ChatApiError("The agent returned a different thread ID.");
  return parsed;
}
```

Types protect local code but not runtime callers or the network boundary. The client refuses to send an empty message or a null/invalid UUID, then validates every response field. A mismatched response thread is rejected rather than silently changing conversation state. React renders answer text, never HTML. Network, HTTP, JSON, shape, and thread failures become useful messages.

### `frontend/src/api.test.ts`

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { postChat } from "./api";

const id = "c6cbdc9b-cf80-41bd-87f7-454a8478c0a6";
describe("postChat", () => {
  const fetchMock = vi.fn<typeof fetch>();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubEnv("VITE_AGENT_URL", "http://localhost:8001/");
    vi.stubGlobal("fetch", fetchMock);
  });

  it("posts and validates the canonical contract", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({
      answer: "LT-100 is available.", thread_id: id,
      tool_rounds: 1, soft_limit_reached: false,
    }), {status: 200, headers: {"Content-Type": "application/json"}}));
    await expect(postChat({message: "Find LT-100", thread_id: id}))
      .resolves.toEqual({
        answer: "LT-100 is available.",
        thread_id: id,
        tool_rounds: 1,
        soft_limit_reached: false,
      });
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8001/chat",
      expect.objectContaining({method: "POST", body: JSON.stringify({
        message: "Find LT-100", thread_id: id,
      })}));
  });

  it("rejects malformed success data", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({answer: "bad"}), {
      status: 200, headers: {"Content-Type": "application/json"},
    }));
    await expect(postChat({message: "Find", thread_id: id}))
      .rejects.toThrow("invalid response");
  });

  it("surfaces HTTP detail", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({detail: "Not ready"}), {
      status: 503, headers: {"Content-Type": "application/json"},
    }));
    await expect(postChat({message: "Find", thread_id: id}))
      .rejects.toMatchObject({status: 503, message: "Agent request failed (503). Not ready"});
  });

  it("never sends an invalid thread ID", async () => {
    await expect(postChat({message: "Find", thread_id: ""}))
      .rejects.toThrow("valid thread ID");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a response for a different thread", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({
      answer: "Wrong conversation.",
      thread_id: "a7bb67e1-88ae-4da7-bb97-2141e1a3238f",
      tool_rounds: 0,
      soft_limit_reached: false,
    }), {status: 200, headers: {"Content-Type": "application/json"}}));
    await expect(postChat({message: "Continue", thread_id: id}))
      .rejects.toThrow("different thread ID");
  });
});
```

## Per-tab UUID

### `frontend/src/thread.ts`

```ts
export const THREAD_STORAGE_KEY = "ops-agent.thread-id";
const valid = (v: string | null): v is string =>
  v !== null &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v);

export function getThreadId(
  storage: Pick<Storage, "getItem" | "setItem"> = window.sessionStorage,
  create: () => string = () => crypto.randomUUID(),
): string {
  const stored = storage.getItem(THREAD_STORAGE_KEY);
  if (valid(stored)) return stored;

  const id = create();
  if (!valid(id)) throw new Error("Thread ID generator returned an invalid UUID.");
  storage.setItem(THREAD_STORAGE_KEY, id);
  return id;
}
```

`sessionStorage` survives reloads but normally scopes state to one tab. The helper reuses a valid stored UUID; otherwise it generates, validates, and stores one before returning. It has no nullable or server-generated path. If browser policy blocks `sessionStorage`, initialization fails instead of silently creating a different persistence model. `localStorage` would incorrectly share a conversation across tabs. Explicitly duplicated tabs can inherit a copy in some browsers, so this is browser-session isolation, not a security boundary.

### `frontend/src/thread.test.ts`

```ts
import { describe, expect, it, vi } from "vitest";
import { getThreadId, THREAD_STORAGE_KEY } from "./thread";

const oldId = "c6cbdc9b-cf80-41bd-87f7-454a8478c0a6";
const newId = "a7bb67e1-88ae-4da7-bb97-2141e1a3238f";
function store(initial?: string) {
  const data = new Map<string, string>();
  if (initial) data.set(THREAD_STORAGE_KEY, initial);
  return {
    getItem: vi.fn((k: string) => data.get(k) ?? null),
    setItem: vi.fn((k: string, v: string) => data.set(k, v)),
  };
}
describe("getThreadId", () => {
  it("reuses a valid ID", () => expect(getThreadId(store(oldId), () => newId)).toBe(oldId));
  it("stores a new ID", () => {
    const storage = store();
    expect(getThreadId(storage, () => newId)).toBe(newId);
    expect(storage.setItem).toHaveBeenCalledWith(THREAD_STORAGE_KEY, newId);
  });
  it("generates only once and reuses the stored value", () => {
    const storage = store();
    const create = vi.fn(() => newId);
    expect(getThreadId(storage, create)).toBe(newId);
    expect(getThreadId(storage, create)).toBe(newId);
    expect(create).toHaveBeenCalledOnce();
    expect(storage.setItem).toHaveBeenCalledOnce();
  });
  it("replaces malformed data", () =>
    expect(getThreadId(store("bad"), () => newId)).toBe(newId));
  it("rejects an invalid generated value", () =>
    expect(() => getThreadId(store(), () => "bad")).toThrow("invalid UUID"));
});
```

## Components

### `frontend/src/components/MessageList.tsx`

```tsx
import { useEffect, useRef } from "react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  softLimitReached?: boolean;
}
export function MessageList({messages, loading}: {
  messages: ChatMessage[]; loading: boolean;
}) {
  const end = useRef<HTMLLIElement>(null);
  useEffect(() => end.current?.scrollIntoView({block: "nearest"}), [messages, loading]);
  if (!messages.length) return <div className="empty">
    <p>Ask about assets, stale inventory, users, or checkout history.</p>
    <p>Try “Find LT-100” or “What is checked out to Maya?”</p>
  </div>;
  return <ol className="messages" aria-label="Conversation" aria-live="polite"
    aria-relevant="additions" aria-busy={loading}>
    {messages.map((m) => <li className={`message ${m.role}`} key={m.id}>
      <span className="label">{m.role === "user" ? "You" : "Ops Agent"}</span>
      <p>{m.text}</p>
      {m.softLimitReached && <p className="note">
        The agent reached its tool-use limit and returned its best available answer.
      </p>}
    </li>)}
    {loading && <li className="thinking" role="status">
      <span aria-hidden="true" />Ops Agent is working…
    </li>}
    <li ref={end} aria-hidden="true" />
  </ol>;
}
```

The type permits only user and assistant messages. The ordered live region announces additions; visible labels do not depend on color. Scrolling uses no smooth animation.

### `frontend/src/components/ChatComposer.tsx`

```tsx
import { useRef, type FormEvent, type KeyboardEvent } from "react";

export function ChatComposer({value, loading, onChange, onSubmit}: {
  value: string; loading: boolean;
  onChange: (value: string) => void; onSubmit: () => void;
}) {
  const form = useRef<HTMLFormElement>(null);
  const composing = useRef(false);
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!loading && value.trim()) onSubmit();
  }
  function keyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !composing.current &&
        !e.nativeEvent.isComposing && !loading) {
      e.preventDefault();
      form.current?.requestSubmit();
    }
  }
  return <form className="composer" ref={form} onSubmit={submit}>
    <label htmlFor="chat-message">Message</label>
    <div className="controls">
      <textarea id="chat-message" value={value} rows={3} maxLength={4000}
        placeholder="Ask a read-only operations question…" disabled={loading}
        aria-describedby="composer-help"
        onChange={(e) => onChange(e.target.value)} onKeyDown={keyDown}
        onCompositionStart={() => { composing.current = true; }}
        onCompositionEnd={() => { composing.current = false; }} />
      <button type="submit" disabled={loading || !value.trim()}>
        {loading ? "Sending…" : "Send"}
      </button>
    </div>
    <p id="composer-help" className="help">Enter sends. Shift+Enter adds a new line.</p>
  </form>;
}
```

The semantic form supports mouse, touch, keyboard, and assistive technology. Enter submits, Shift+Enter inserts a line, and both composition checks prevent IME selection from submitting. Loading disables concurrent turns.

### `frontend/src/components/ChatComposer.test.tsx`

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ChatComposer } from "./ChatComposer";

function Harness({submit}: {submit: () => void}) {
  const [value, setValue] = useState("");
  return <ChatComposer value={value} loading={false} onChange={setValue} onSubmit={submit} />;
}
describe("ChatComposer", () => {
  it("sends with Enter", async () => {
    const submit = vi.fn(); render(<Harness submit={submit} />);
    await userEvent.type(screen.getByLabelText("Message"), "Find LT-100{Enter}");
    expect(submit).toHaveBeenCalledOnce();
  });
  it("keeps Shift+Enter as a newline", async () => {
    const submit = vi.fn(); render(<Harness submit={submit} />);
    const input = screen.getByLabelText("Message");
    await userEvent.type(input, "One{Shift>}{Enter}{/Shift}Two");
    expect(input).toHaveValue("One\nTwo"); expect(submit).not.toHaveBeenCalled();
  });
  it("does not send during composition", () => {
    const submit = vi.fn(); render(<Harness submit={submit} />);
    const input = screen.getByLabelText("Message");
    fireEvent.change(input, {target: {value: "編集中"}});
    fireEvent.compositionStart(input); fireEvent.keyDown(input, {key: "Enter"});
    expect(submit).not.toHaveBeenCalled();
  });
});
```

## Application

### `frontend/src/App.tsx`

```tsx
import { useEffect, useRef, useState } from "react";
import { postChat } from "./api";
import { ChatComposer } from "./components/ChatComposer";
import { MessageList, type ChatMessage } from "./components/MessageList";
import { getThreadId } from "./thread";

export default function App() {
  const [threadId] = useState(() => getThreadId());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);

  async function send() {
    const message = draft.trim();
    if (!message || loading) return;
    setMessages((v) => [...v, {id: crypto.randomUUID(), role: "user", text: message}]);
    setDraft(""); setError(null); setLoading(true);
    const controller = new AbortController(); active.current = controller;
    try {
      const result = await postChat({message, thread_id: threadId}, controller.signal);
      setMessages((v) => [...v, {
        id: crypto.randomUUID(), role: "assistant", text: result.answer,
        softLimitReached: result.soft_limit_reached,
      }]);
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      setError(caught instanceof Error ? caught.message : "An unexpected error occurred.");
    } finally {
      if (active.current === controller) {
        active.current = null; setLoading(false);
      }
    }
  }

  return <main className="shell"><section className="card" aria-labelledby="title">
    <header><div><p className="eyebrow">Read-only asset assistant</p>
      <h1 id="title">Ops Agent</h1></div></header>
    <div className="transcript"><MessageList messages={messages} loading={loading} /></div>
    {error && <div className="error" role="alert">
      <strong>Message not completed.</strong><span>{error}</span>
    </div>}
    <ChatComposer value={draft} loading={loading} onChange={setDraft} onSubmit={send} />
  </section></main>;
}
```

The user turn is rendered optimistically. Only the final `answer` is appended later. The returned `thread_id` is consumed by runtime validation and equality checking; it never replaces the tab-generated value. `tool_rounds` is validated but intentionally not rendered, while `soft_limit_reached` controls the short final-answer note. Errors are separate alerts, leave the attempted user turn visible, and restore controls. One loading flag serializes turns; unmount aborts the active request.

### `frontend/src/main.tsx`

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element was not found.");
createRoot(root).render(<StrictMode><App /></StrictMode>);
```

### `frontend/src/App.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { postChat } from "./api";
import App from "./App";
import { THREAD_STORAGE_KEY } from "./thread";

vi.mock("./api", () => ({postChat: vi.fn()}));
const mocked = vi.mocked(postChat);
const id = "c6cbdc9b-cf80-41bd-87f7-454a8478c0a6";
describe("App", () => {
  beforeEach(() => {
    mocked.mockReset();
    sessionStorage.setItem(THREAD_STORAGE_KEY, id);
  });
  it("shows the user and final answer, not tool rounds", async () => {
    mocked.mockResolvedValue({answer: "Maya has LT-100.", thread_id: id,
      tool_rounds: 3, soft_limit_reached: false});
    render(<App />); const user = userEvent.setup();
    await user.type(screen.getByLabelText("Message"), "Who has LT-100?");
    await user.click(screen.getByRole("button", {name: "Send"}));
    expect(screen.getByText("Who has LT-100?")).toBeInTheDocument();
    expect(await screen.findByText("Maya has LT-100.")).toBeInTheDocument();
    expect(screen.queryByText("3")).not.toBeInTheDocument();
    expect(mocked).toHaveBeenCalledWith(
      {message: "Who has LT-100?", thread_id: id}, expect.any(AbortSignal));
  });
  it("generates, stores, and sends one thread UUID when the tab has none", async () => {
    sessionStorage.clear();
    mocked.mockImplementation(async (request) => ({
      answer: "No matching assets.",
      thread_id: request.thread_id,
      tool_rounds: 1,
      soft_limit_reached: false,
    }));
    render(<App />);
    const stored = sessionStorage.getItem(THREAD_STORAGE_KEY);
    if (!stored) throw new Error("Expected a stored thread UUID.");
    expect(stored).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Message"), "Find missing assets");
    await user.click(screen.getByRole("button", {name: "Send"}));
    expect(mocked).toHaveBeenCalledWith(
      {message: "Find missing assets", thread_id: stored},
      expect.any(AbortSignal),
    );
    expect(sessionStorage.getItem(THREAD_STORAGE_KEY)).toBe(stored);
  });
  it("announces a handled failure and unlocks input", async () => {
    mocked.mockRejectedValue(new Error("Agent request failed (503)."));
    render(<App />); const user = userEvent.setup();
    await user.type(screen.getByLabelText("Message"), "Find LT-999");
    await user.click(screen.getByRole("button", {name: "Send"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("503");
    expect(screen.getByLabelText("Message")).toBeEnabled();
  });
});
```

### `frontend/src/test/setup.ts`

```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});
```

Tests mock the agent and require no Anthropic or LangSmith secret.

## Responsive CSS

### `frontend/src/styles.css`

```css
:root{color:#102a43;background:#eef3f8;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
*{box-sizing:border-box}html,body,#root{min-height:100%;margin:0}button,textarea{font:inherit}
.shell{min-height:100dvh;display:grid;place-items:center;padding:1.5rem;background:#eef3f8}
.card{width:min(100%,52rem);height:min(48rem,calc(100dvh - 3rem));min-height:34rem;
display:grid;grid-template-rows:auto minmax(0,1fr) auto auto;overflow:hidden;background:#fff;
border:1px solid #c7d5e0;border-radius:1rem;box-shadow:0 1rem 3rem rgb(16 42 67/12%)}
header{padding:1.2rem 1.5rem;color:#fff;background:#102a43}header h1,header p{margin:0}
.eyebrow{color:#b9d8ee;font-size:.75rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.transcript{min-height:0;overflow-y:auto;padding:1.5rem;background:#f7fafc}
.empty{min-height:100%;display:grid;place-content:center;text-align:center;color:#526d82}
.empty p{margin:.3rem}.messages{display:flex;flex-direction:column;gap:1rem;margin:0;padding:0;list-style:none}
.message{width:fit-content;max-width:min(88%,42rem);padding:.8rem 1rem;border-radius:.9rem}
.message p{margin:.3rem 0 0;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.55}
.message.user{align-self:flex-end;color:#fff;background:#1769aa;border-bottom-right-radius:.25rem}
.message.assistant{align-self:flex-start;background:#fff;border:1px solid #c7d5e0;border-bottom-left-radius:.25rem}
.label{font-size:.72rem;font-weight:800;text-transform:uppercase}.note{padding-top:.5rem;border-top:1px solid #c7d5e0;color:#526d82;font-size:.85rem}
.thinking{display:flex;align-items:center;gap:.5rem;color:#486581}.thinking span{width:.65rem;height:.65rem;border-radius:50%;background:#1769aa;animation:pulse 1.2s infinite}
.error{display:flex;gap:.75rem;padding:.75rem 1.5rem;color:#7f1d1d;background:#fef2f2;border-top:1px solid #fecaca}
.composer{padding:1rem 1.5rem 1.2rem;border-top:1px solid #d9e2ec}.composer>label{display:block;margin-bottom:.45rem;font-weight:700}
.controls{display:flex;gap:.75rem}.controls textarea{flex:1;min-width:0;resize:vertical;padding:.75rem;border:1px solid #9fb3c8;border-radius:.6rem}
textarea:focus-visible,button:focus-visible{outline:3px solid #f6c344;outline-offset:2px}
button{min-width:6rem;padding:.75rem 1rem;color:#fff;font-weight:700;background:#1769aa;border:0;border-radius:.6rem;cursor:pointer}
button:hover:not(:disabled){background:#0f548c}button:disabled{cursor:not-allowed;opacity:.58}
.help{margin:.45rem 0 0;color:#526d82;font-size:.8rem}@keyframes pulse{50%{opacity:.35;transform:scale(.8)}}
@media(max-width:40rem){.shell{display:block;padding:0}.card{width:100%;height:100dvh;min-height:100dvh;border:0;border-radius:0}
header,.transcript,.composer{padding-left:1rem;padding-right:1rem}.message{max-width:94%}.controls{flex-direction:column}.error{flex-direction:column}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
```

The layout becomes full-screen on small displays. Text wraps long identifiers, controls retain visible focus and sufficient contrast, and labels avoid color-only meaning. The reduced-motion query disables the nonessential loading pulse and future transitions.

## Nginx and container

### `frontend/nginx.conf`

```nginx
server {
    listen 5173;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    charset utf-8;
    server_tokens off;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header X-Frame-Options "DENY" always;
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    location = /index.html {
        expires -1;
        try_files $uri =404;
    }
    location /assets/ {
        expires 1y;
        try_files $uri =404;
    }
    location / { try_files $uri $uri/ /index.html; }
}
```

Hashed assets receive a one-year expiry; HTML revalidates. `try_files` permits future client routes. Nginx does not proxy chat in this design, so agent CORS remains required.

### `frontend/Dockerfile`

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json tsconfig.app.json tsconfig.node.json vite.config.ts ./
COPY index.html ./
COPY src ./src
ARG VITE_AGENT_URL=http://localhost:8001
ENV VITE_AGENT_URL=$VITE_AGENT_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 5173
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD wget -qO- http://127.0.0.1:5173/ >/dev/null || exit 1
```

The final image contains no Node runtime, source, or dev dependencies. Build a different public URL with `docker build --build-arg VITE_AGENT_URL=https://agent.example.com ...`; runtime environment changes do not rewrite static assets.

### `frontend/.dockerignore`

```dockerignore
node_modules
dist
coverage
.env*
*.log
.git
.gitignore
```

## Commands and verification

```bash
cd frontend
npm install
npm run typecheck
npm run lint
npm test
npm run build
```

Then copy `.env.example` to `.env.local`, start the agent on port 8001, run `npm run dev`, and open `http://localhost:5173`. Verify:

1. A user message appears immediately and one final answer follows.
2. A follow-up uses prior context; reload preserves context in that tab.
3. A normally opened new tab has a different `sessionStorage["ops-agent.thread-id"]`.
4. Stopping the agent produces an alert and re-enables controls.
5. Enter sends; Shift+Enter inserts a newline; IME Enter does not send.
6. Tab focus is visible; a screen reader announces answers/errors.
7. Reduced-motion preference stops repeated loading animation.
8. The DOM never contains tool arguments/results or `tool_rounds`.

Container verification:

```bash
docker build --build-arg VITE_AGENT_URL=http://localhost:8001 \
  -t ops-agent-frontend frontend
docker run --rm -p 5173:5173 ops-agent-frontend
curl --fail http://localhost:5173/
```

The browser, not the frontend container, makes `POST /chat`; the built URL must therefore be browser-reachable.

## Definition of done and pitfalls

- [ ] Generated `package-lock.json` is committed; all four npm checks pass.
- [ ] The request is exactly `{message,thread_id}`; a null or invalid UUID is never sent; all four response fields are runtime-validated.
- [ ] A valid UUID is generated and stored once per tab, then reused; mismatched response threads fail.
- [ ] Only user text and final `answer` values are transcript messages.
- [ ] Loading serializes requests; handled errors restore a usable UI.
- [ ] Enter/Shift+Enter/IME, live regions, focus, contrast, mobile layout, and reduced motion are verified.
- [ ] Nginx serves and health-checks on 5173.

Common mistakes are using Docker-only `http://agent:8001` in browser code, expecting runtime replacement of Vite variables, trusting TypeScript instead of validating JSON, generating a new thread UUID per message, using cross-tab `localStorage`, rendering all LangGraph messages, ignoring IME composition, allowing concurrent turns, attempting to fix CORS in the client, and hand-writing `package-lock.json`.
