// Smoke/structural test confirming the React + TypeScript frontend renders.
// Verifies the app shell mounts the view layer within the journey provider
// (Requirements 14.1, 14.5).

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App shell", () => {
  it("renders the four journey views", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "E-Commerce Stage 1", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Catalog" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cart" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Account" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Checkout" }),
    ).toBeInTheDocument();
  });
});
