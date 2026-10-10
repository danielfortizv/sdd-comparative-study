// Property-based test for the Checkout view's empty-cart guard (design:
// Frontend Components — Checkout; Testing Strategy — Property-Based Tests).
//
// Feature: ecommerce-stage1, Property 15: Checkout is reachable only when the
// cart is non-empty
//
// Validates: Requirements 9.5
//
// Proceeding to checkout as a valid purchase is permitted if and only if the
// cart is non-empty. With the session held ACTIVE (so the identification gate
// never decides the outcome and the empty-cart guard is the sole deciding
// factor), the "complete-purchase" control — the only control that lets a
// valid purchase proceed — is present IF AND ONLY IF the cart is non-empty.
// When the cart is empty the view shows the "checkout-empty-state" indication
// and renders no completion control.

import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import fc from "fast-check";
import { afterEach, describe, expect, it } from "vitest";
import type { ReactNode } from "react";
import { useEffect } from "react";

import type { Product } from "../types";
import { JourneyProvider, useJourney } from "../state/JourneyState";
import { CheckoutView } from "./CheckoutView";

// A fixed, small catalog the generated carts reference. The property holds for
// any catalog, so a representative fixed set keeps the input space focused.
const CATALOG: Product[] = [
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
  {
    id: "p3",
    name: "Eraser",
    imageUrl: "https://example.test/p3.png",
    description: "A soft eraser.",
    price: 0.75,
    available: false,
  },
];

const PRODUCT_IDS = CATALOG.map((product) => product.id);

/** A single add action seeding the cart: a product id and a positive quantity. */
const addActionArb = fc.record({
  productId: fc.constantFrom(...PRODUCT_IDS),
  quantity: fc.integer({ min: 1, max: 5 }),
});

// A cart generator that yields an empty array sometimes and a non-empty array
// other times, so both sides of the biconditional are exercised.
const cartArb = fc.array(addActionArb, { minLength: 0, maxLength: 6 });

// Seeds the catalog, signs the session in on mount so the identification gate
// is satisfied, and exposes an add control per catalog product so a generated
// cart can be built via the real journey state.
function Harness({ children }: { children: ReactNode }) {
  const { setCatalog, addToCart, signInSession } = useJourney();
  useEffect(() => {
    setCatalog(CATALOG);
    signInSession("buyer@example.test");
  }, [setCatalog, addToCart, signInSession]);
  return (
    <>
      {CATALOG.map((product) => (
        <button
          key={product.id}
          type="button"
          onClick={() => addToCart(product.id, 1)}
        >
          {`Add ${product.id}`}
        </button>
      ))}
      {children}
    </>
  );
}

afterEach(() => {
  cleanup();
});

describe("Property 15: Checkout is reachable only when the cart is non-empty", () => {
  it("renders the complete-purchase control iff the cart is non-empty (session active)", () => {
    fc.assert(
      fc.property(cartArb, (adds) => {
        render(
          <JourneyProvider>
            <Harness>
              <CheckoutView />
            </Harness>
          </JourneyProvider>,
        );

        // Seed the generated cart via the real add controls. The session is
        // already active from the harness mount effect.
        act(() => {
          for (const add of adds) {
            const button = screen.getByRole("button", {
              name: `Add ${add.productId}`,
            });
            for (let i = 0; i < add.quantity; i += 1) {
              fireEvent.click(button);
            }
          }
        });

        const cartIsNonEmpty = adds.length > 0;
        const completeControl = screen.queryByTestId("complete-purchase");
        const emptyState = screen.queryByTestId("checkout-empty-state");

        // Biconditional: the valid-purchase control exists exactly when the
        // cart is non-empty.
        expect(completeControl !== null).toBe(cartIsNonEmpty);

        if (cartIsNonEmpty) {
          // A valid purchase can proceed: the control is present and the
          // empty-state indication is absent.
          expect(completeControl).toBeInTheDocument();
          expect(emptyState).not.toBeInTheDocument();
        } else {
          // No valid purchase can proceed: the empty-state indication is shown
          // and no completion control exists.
          expect(emptyState).toBeInTheDocument();
          expect(completeControl).not.toBeInTheDocument();
        }

        cleanup();
      }),
    );
  });
});
