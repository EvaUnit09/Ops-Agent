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
