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
