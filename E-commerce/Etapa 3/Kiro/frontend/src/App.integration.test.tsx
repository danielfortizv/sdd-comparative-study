// App-level integration-wiring tests for the integrated journey (task 14.3).
//
// Verifies the shell presents the Catalog, Cart, Account, and Checkout as one
// integrated system (R11.1): an accessible navigation exposes each view, every
// view is mounted so cross-view state stays consistent, and the Account
// section carries id="account" so the Checkout identification gate's
// "#account" sign-in/register links resolve.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App integrated journey wiring", () => {
  it("exposes accessible navigation to each view of the journey", () => {
    render(<App />);

    const nav = screen.getByRole("navigation", { name: "Journey navigation" });
    expect(nav).toBeInTheDocument();

    for (const label of ["Catalog", "Cart", "Account", "Checkout"]) {
      const link = screen.getByRole("link", { name: label });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", `#${label.toLowerCase()}`);
    }
  });

  it("mounts all four views so journey state stays consistent across them", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Catalog" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cart" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Account" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Checkout" }),
    ).toBeInTheDocument();
  });

  it("provides an #account anchor target for the Checkout identification gate", () => {
    const { container } = render(<App />);

    const accountAnchor = container.querySelector("#account");
    expect(accountAnchor).not.toBeNull();
    // The Account view (AuthView) renders inside the anchor target, so the
    // Checkout gate's href="#account" links reach the sign-in/register options.
    expect(accountAnchor).toContainElement(
      screen.getByRole("heading", { name: "Account" }),
    );
  });
});
