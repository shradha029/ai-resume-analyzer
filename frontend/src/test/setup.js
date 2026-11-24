import "@testing-library/jest-dom/vitest";
import React from "react";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});

// jsdom has no layout engine: give Recharts' ResponsiveContainer a fixed size so charts really render.
vi.mock("recharts", async () => {
  const actual = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }) =>
      React.createElement("div", { style: { width: 500, height: 300 } }, React.cloneElement(children, { width: 500, height: 300 })),
  };
});

window.confirm = vi.fn(() => true);
