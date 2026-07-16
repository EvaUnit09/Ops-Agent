import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom does not implement scrollIntoView; MessageList calls it on every
// render, so tests need a stub even though real browsers provide it.
Element.prototype.scrollIntoView = () => {};

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});
