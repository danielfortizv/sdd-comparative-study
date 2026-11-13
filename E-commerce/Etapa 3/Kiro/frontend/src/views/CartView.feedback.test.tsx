// Example-based unit tests for the Cart view's feedback and empty state
// (Task 9.4; design: Frontend Components — Cart; Testing Strategy — Unit and
// Example Tests).
//
// These focus specifically on the three deliverables of task 9.4:
//   1. The add confirmation surfaced when a product is added (R2.2).
//   2. The removal confirmation that names the removed product (R3.3).
//   3. The empty-state indication shown when no products are present, and its
//      reappearance after the last item is removed (R3.4).
//
// Adds originate from the catalog but are reflected in the Cart automatically
// from shared journey state, so the harness seeds the catalog (so cart items
// resolve) and exposes catalog-style add buttons, mirroring CartView.test.tsx.

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ReactNode } from "react";
import { useEffect } from "react";

import type { Product } from "../types";
import { JourneyProvider, useJourney } from "../state/JourneyState";
import { CartView } from "./CartView";

const PRODUCTS: Product[] = [
  {
    id: "p1",
    name: "Notebook",
    imageUrl: "https://example.test/p1.png",
    description: "A ruled notebook.",
    price: 4.5,
    available: true,
  },
  {
    id: "p2",
    name: "Pen",
    imageUrl: "https://example.test/p2.png",
    description: "A blue pen.",
    price: 1.25,
    available: true,
  },
];

function Harness({ children }: { children: ReactNode }) {
  const { setCatalog, addToCart } = useJourney();
  useEffect(() => {
    setCatalog(PRODUCTS);
  }, [setCatalog]);
  return (
    <>
      {PRODUCTS.map((product) => (
        <button
          key={product.id}
          type="button"
          onClick={() => addToCart(product.id, 1)}
        >
          {`Add ${product.name}`}
        </button>
      ))}
      {children}
    </>
  );
}

function renderCart() {
  return render(
    <JourneyProvider>
      <Harness>
        <CartView />
      </Harness>
    </JourneyProvider>,
  );
}

describe("CartView feedback and empty state (Task 9.4)", () => {
  // R2.2: adding a product surfaces a visible add confirmation.
  it("shows an add confirmation when a product is added", () => {
    renderCart();

    const confirmation = screen.getByTestId("cart-confirmation");
    // No confirmation is announced before any add action.
    expect(confirmation).toHaveTextContent("");

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));

    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent(/added/i);
  });

  it("re-announces the add confirmation when another product is added", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));
    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent(/added/i);

    fireEvent.click(screen.getByRole("button", { name: "Add Pen" }));
    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent(/added/i);
  });

  // R3.3: removing a product surfaces a visible removal confirmation that
  // names the specific product removed.
  it("shows a removal confirmation naming the removed product", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));
    fireEvent.click(screen.getByRole("button", { name: "Add Pen" }));

    fireEvent.click(
      screen.getByRole("button", { name: "Remove Notebook from cart" }),
    );

    const confirmation = screen.getByTestId("cart-confirmation");
    expect(confirmation).toHaveTextContent(/Notebook was removed/i);
    // The confirmation names the removed product specifically, not the one
    // that is still present.
    expect(confirmation).not.toHaveTextContent(/Pen was removed/i);
    // The removed product is gone while the other remains.
    expect(screen.queryByTestId("cart-item-p1")).not.toBeInTheDocument();
    expect(screen.getByTestId("cart-item-p2")).toBeInTheDocument();
  });

  it("names the correct product when a different product is removed", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));
    fireEvent.click(screen.getByRole("button", { name: "Add Pen" }));

    fireEvent.click(
      screen.getByRole("button", { name: "Remove Pen from cart" }),
    );

    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent(
      /Pen was removed/i,
    );
  });

  // R3.4: the empty-state indication shows when no products are present.
  it("shows the empty-state indication when the cart has no products", () => {
    renderCart();

    expect(screen.getByTestId("cart-empty-state")).toBeInTheDocument();
    // No cart items or total are shown while empty.
    expect(screen.queryByTestId("cart-item-p1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cart-total")).not.toBeInTheDocument();
  });

  it("hides the empty-state once a product is present", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));

    expect(screen.queryByTestId("cart-empty-state")).not.toBeInTheDocument();
    expect(
      within(screen.getByTestId("cart-item-p1")).getByTestId("cart-item-name"),
    ).toHaveTextContent("Notebook");
  });

  // R3.4: the empty-state indication reappears after the last item is removed.
  it("shows the empty-state again after the last product is removed", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Pen" }));
    expect(screen.queryByTestId("cart-empty-state")).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Remove Pen from cart" }),
    );

    expect(screen.getByTestId("cart-empty-state")).toBeInTheDocument();
    expect(screen.queryByTestId("cart-total")).not.toBeInTheDocument();
  });
});
