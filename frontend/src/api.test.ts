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
