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
