// Property-based test for the shared journey state container (design: Testing
// Strategy — Property-Based Tests; Shared Journey State).
//
// Feature: ecommerce-stage1, Property 4: Cart contents are preserved across
// journey navigation
//
// Validates: Requirements 3.5
//
// For any cart state and any sequence of non-mutating journey navigations
// (changing which view is displayed, re-reading the derived cart view, toggling
// the session via sign-in/sign-out, or reloading the same catalog), the cart's
// authoritative CartItem contents remain unchanged. The test exercises the real
// JourneyProvider / useJourney container rather than the pure layer so the
// preservation invariant is demonstrated on the live state.

import { act, renderHook } from "@testing-library/react";
import fc from "fast-check";
import { describe, expect, it } from "vitest";

import type { Product } from "../types";
import { JourneyProvider, useJourney } from "./JourneyState";

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

/** An add action seeding the cart: a product id and a positive quantity. */
const addActionArb = fc.record({
  productId: fc.constantFrom(...PRODUCT_IDS),
  quantity: fc.integer({ min: 1, max: 9 }),
});

/**
 * The non-mutating journey navigations under test. None of these is an add,
 * remove, or quantity-change action, so each must leave the cart contents
 * unchanged (Requirement 3.5).
 */
type NavAction =
  | { kind: "navigate" } // change which view is displayed (no state change)
  | { kind: "readCartView" } // read the derived cart view
  | { kind: "signIn"; identity: string } // session change, not a cart change
  | { kind: "signOut" } // session change, not a cart change
  | { kind: "reloadCatalog" }; // load the same catalog again

const navActionArb: fc.Arbitrary<NavAction> = fc.oneof(
  fc.constant<NavAction>({ kind: "navigate" }),
  fc.constant<NavAction>({ kind: "readCartView" }),
  fc
    .string({ minLength: 1, maxLength: 12 })
    .map<NavAction>((identity) => ({ kind: "signIn", identity })),
  fc.constant<NavAction>({ kind: "signOut" }),
  fc.constant<NavAction>({ kind: "reloadCatalog" }),
);

describe("Property 4: Cart contents are preserved across journey navigation", () => {
  it("leaves cart contents unchanged across any sequence of non-mutating navigations", () => {
    fc.assert(
      fc.property(
        fc.array(addActionArb, { maxLength: 12 }),
        fc.array(navActionArb, { maxLength: 20 }),
        (seedAdds, navigations) => {
          const { result } = renderHook(() => useJourney(), {
            wrapper: JourneyProvider,
          });

          // Load the catalog and seed a random cart via add actions. These are
          // the only mutating operations; everything after this point must
          // preserve the cart.
          act(() => {
            result.current.setCatalog(CATALOG);
            for (const add of seedAdds) {
              result.current.addToCart(add.productId, add.quantity);
            }
          });

          // Snapshot the authoritative cart contents before navigating.
          const before = result.current.cart.map((item) => ({ ...item }));

          // Apply the generated sequence of non-mutating navigations.
          act(() => {
            for (const action of navigations) {
              switch (action.kind) {
                case "navigate":
                  // Switching views is a UI-level concern that touches no
                  // journey state; modeled as a no-op read of the container.
                  void result.current.cart;
                  break;
                case "readCartView":
                  void result.current.cartView;
                  break;
                case "signIn":
                  result.current.signInSession(action.identity);
                  break;
                case "signOut":
                  result.current.signOutSession();
                  break;
                case "reloadCatalog":
                  result.current.setCatalog(CATALOG);
                  break;
              }
            }
          });

          const after = result.current.cart.map((item) => ({ ...item }));

          // Cart CartItem list is unchanged: same product ids and quantities,
          // in the same order.
          expect(after).toEqual(before);
        },
      ),
    );
  });
});
