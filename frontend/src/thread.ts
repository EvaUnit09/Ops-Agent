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
