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
