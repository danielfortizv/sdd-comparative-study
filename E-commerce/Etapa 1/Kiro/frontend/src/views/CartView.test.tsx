// Example-based unit tests for the Cart view (design: Frontend Components —
// Cart; Testing Strategy — Unit and Example Tests).
//
// These cover the display of each product/quantity/unit price/line total and
// the accumulated total (R3.1), quantity adjustment updating quantity and total
// while keeping unit price consistent (R3.2), removal with a visible
// confirmation (R3.3), the empty-state indication (R3.4), and the automatic
// add confirmation surfaced when the cart gains an item (R2.2, R2.3).

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

// Seeds the catalog (so cart items resolve) and exposes catalog-style add
// controls, mirroring how adds originate in the Catalog and are reflected in
// the Cart automatically from shared state.
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

describe("CartView", () => {
  it("shows an empty-state indication when there are no products", () => {
    renderCart();
    expect(screen.getByTestId("cart-empty-state")).toBeInTheDocument();
    expect(screen.queryByTestId("cart-total")).not.toBeInTheDocument();
  });

  it("displays each product with its quantity, unit price, line total, and the accumulated total", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));
    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));
    fireEvent.click(screen.getByRole("button", { name: "Add Pen" }));

    const notebook = within(screen.getByTestId("cart-item-p1"));
    expect(notebook.getByTestId("cart-item-name")).toHaveTextContent("Notebook");
    expect(notebook.getByTestId("cart-item-quantity")).toHaveTextContent("2");
    expect(notebook.getByTestId("cart-item-unit-price")).toHaveTextContent(
      "$4.50",
    );
    expect(notebook.getByTestId("cart-item-line-total")).toHaveTextContent(
      "$9.00",
    );

    const pen = within(screen.getByTestId("cart-item-p2"));
    expect(pen.getByTestId("cart-item-quantity")).toHaveTextContent("1");
    expect(pen.getByTestId("cart-item-unit-price")).toHaveTextContent("$1.25");

    // Accumulated total = 9.00 + 1.25 = 10.25 (R3.1).
    expect(screen.getByTestId("cart-total")).toHaveTextContent("$10.25");
  });

  it("surfaces a visible add confirmation when the cart gains an item", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));

    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent(
      /added/i,
    );
  });

  it("updates quantity and total on adjustment while keeping the unit price consistent", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));

    const notebook = within(screen.getByTestId("cart-item-p1"));
    expect(notebook.getByTestId("cart-item-quantity")).toHaveTextContent("1");
    expect(screen.getByTestId("cart-total")).toHaveTextContent("$4.50");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Increase quantity of Notebook",
      }),
    );

    const notebookAfter = within(screen.getByTestId("cart-item-p1"));
    // Quantity and total updated immediately...
    expect(notebookAfter.getByTestId("cart-item-quantity")).toHaveTextContent(
      "2",
    );
    expect(screen.getByTestId("cart-total")).toHaveTextContent("$9.00");
    // ...while the unit price stays consistent (R3.2).
    expect(notebookAfter.getByTestId("cart-item-unit-price")).toHaveTextContent(
      "$4.50",
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Decrease quantity of Notebook",
      }),
    );
    const notebookDecreased = within(screen.getByTestId("cart-item-p1"));
    expect(
      notebookDecreased.getByTestId("cart-item-quantity"),
    ).toHaveTextContent("1");
    expect(screen.getByTestId("cart-total")).toHaveTextContent("$4.50");
  });

  it("removes a product and shows a visible removal confirmation", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));
    fireEvent.click(screen.getByRole("button", { name: "Add Pen" }));
    expect(screen.getByTestId("cart-item-p1")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Remove Notebook from cart" }),
    );

    expect(screen.queryByTestId("cart-item-p1")).not.toBeInTheDocument();
    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent(
      /Notebook was removed/i,
    );
    // The remaining product is still shown (contents retained, R3.5).
    expect(screen.getByTestId("cart-item-p2")).toBeInTheDocument();
  });

  it("shows the empty-state again once the last product is removed", () => {
    renderCart();

    fireEvent.click(screen.getByRole("button", { name: "Add Pen" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Remove Pen from cart" }),
    );

    expect(screen.getByTestId("cart-empty-state")).toBeInTheDocument();
  });
});
