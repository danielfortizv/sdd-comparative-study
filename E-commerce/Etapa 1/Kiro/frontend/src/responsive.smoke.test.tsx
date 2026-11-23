// Representative responsive-usability example checks for task 14.4 (R13.1).
//
// jsdom cannot compute real layout, so these are representative structural
// checks that the responsive scaffolding exists rather than pixel-perfect
// breakpoint assertions. The approach is the DOM-structure one sanctioned by
// the task: the rendered interface uses the responsive building blocks the
// mobile-first stylesheet targets — a product grid that reflows across
// breakpoints, a navigation that wraps so every destination stays reachable on
// a narrow screen, and a single centered flexible main column shared by every
// view — so the layout stays clear, consistent, and usable from mobile up to
// desktop. (vitest runs with `css: false`, so computed layout and raw CSS text
// are not available here; these structural checks are the reliable signal.)

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Product } from "./types";

vi.mock("./api/client", () => ({
  ApiError: class ApiError extends Error {},
  API_BASE_URL: "http://localhost:8000",
  apiClient: {
    listProducts: vi.fn(),
    getProduct: vi.fn(),
    register: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    confirmCheckout: vi.fn(),
  },
}));

import { apiClient } from "./api/client";
import { App } from "./App";

const CATALOG: Product[] = [
  {
    id: "p-001",
    name: "Wireless Headphones",
    imageUrl: "https://example.test/headphones.png",
    description: "Over-ear wireless headphones.",
    price: 79.99,
    available: true,
  },
  {
    id: "p-002",
    name: "Mechanical Keyboard",
    imageUrl: "https://example.test/keyboard.png",
    description: "Compact mechanical keyboard.",
    price: 120,
    available: true,
  },
];

describe("responsive-usability structure (R13.1)", () => {
  it("renders the responsive product grid the mobile-first stylesheet targets", async () => {
    vi.mocked(apiClient.listProducts).mockResolvedValue(CATALOG);

    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "Wireless Headphones" });

    // The catalog uses the .product-list grid container: a multi-column grid on
    // desktop that collapses to a single column on narrow (mobile) screens.
    const productList = container.querySelector(".product-list");
    expect(productList).not.toBeNull();
    expect(productList?.tagName).toBe("UL");

    // Each product is a flexible card (.product-card) that stretches to the
    // available column width at any breakpoint.
    const cards = container.querySelectorAll(".product-card");
    expect(cards.length).toBe(CATALOG.length);
  });

  it("renders a wrapping navigation and a shared flexible main column", async () => {
    vi.mocked(apiClient.listProducts).mockResolvedValue(CATALOG);

    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "Wireless Headphones" });

    // The in-page navigation wraps so every destination stays reachable on a
    // narrow mobile viewport (and sits inline on desktop).
    const nav = container.querySelector(".journey-nav");
    expect(nav).not.toBeNull();
    const navLinks = nav?.querySelectorAll("a") ?? [];
    expect(navLinks.length).toBe(4);

    // A single centered, flexible main column container is shared by every
    // view, keeping the layout consistent across breakpoints.
    expect(container.querySelector("main")).not.toBeNull();
  });

  it("keeps the whole journey present at both breakpoints without layout gating", async () => {
    vi.mocked(apiClient.listProducts).mockResolvedValue(CATALOG);

    render(<App />);
    await screen.findByRole("heading", { name: "Wireless Headphones" });

    // No view is hidden behind a layout/breakpoint condition: all four journey
    // sections render together, so the journey is usable at mobile and desktop
    // widths alike (R13.1).
    for (const name of ["Catalog", "Cart", "Account", "Checkout"]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
  });
});
