// Property-based test for the identification gate's cart-preservation
// invariant (design: Testing Strategy — Property-Based Tests; Shared Journey
// State; Checkout identification gate).
//
// Feature: ecommerce-stage1, Property 14: Authentication preserves the active cart
//
// Validates: Requirements 8.3, 8.4
//
// When the person signs in (R8.3) or registers (R8.4) during the Active_Journey,
// the Application retains the items in the active cart that existed before the
// authentication action. The authentication action in the app establishes an
// in-memory session via signInSession(identity); the cart lives independently
// in the shared journey state, so authenticating leaves the cart's authoritative
// CartItem list unchanged. The test exercises the real JourneyProvider /
// useJourney container so the invariant is demonstrated on the live state.

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

/** An add action seeding the cart: a catalog product id and a positive quantity. */
const addActionArb = fc.record({
  productId: fc.constantFrom(...PRODUCT_IDS),
  quantity: fc.integer({ min: 1, max: 9 }),
});

/** A generated display identity for the authentication action (sign-in / registration). */
const identityArb = fc.string({ minLength: 1, maxLength: 16 });

describe("Property 14: Authentication preserves the active cart", () => {
  // Feature: ecommerce-stage1, Property 14: Authentication preserves the active cart
  // Validates: Requirements 8.3, 8.4
  it("leaves cart items equal to those before sign-in or registration", () => {
    fc.assert(
      fc.property(
        fc.array(addActionArb, { maxLength: 12 }),
        identityArb,
        identityArb,
        (seedAdds, signInIdentity, registerIdentity) => {
          const { result } = renderHook(() => useJourney(), {
            wrapper: JourneyProvider,
          });

          // Load the catalog and seed a random cart via add actions. These are
          // the only cart-mutating operations; the authentication action that
          // follows must preserve the cart.
          act(() => {
            result.current.setCatalog(CATALOG);
            for (const add of seedAdds) {
              result.current.addToCart(add.productId, add.quantity);
            }
          });

          // Snapshot the authoritative cart contents before authenticating.
          const before = result.current.cart.map((item) => ({ ...item }));

          // The authentication action: sign-in during the Active_Journey
          // establishes a session via signInSession, changing only session
          // state (R8.3).
          act(() => {
            result.current.signInSession(signInIdentity);
          });

          const afterSignIn = result.current.cart.map((item) => ({ ...item }));

          // Cart CartItem list is unchanged: same product ids and quantities,
          // in the same order (R8.3).
          expect(afterSignIn).toEqual(before);
          // The session is now active, confirming an authentication action
          // actually took place.
          expect(result.current.session.active).toBe(true);

          // Registration-style authentication establishing a (different)
          // session is likewise modeled via signInSession and must also leave
          // the cart items equal to those before the authentication action
          // (R8.4).
          act(() => {
            result.current.signInSession(registerIdentity);
          });

          const afterRegister = result.current.cart.map((item) => ({ ...item }));

          expect(afterRegister).toEqual(before);
          expect(result.current.session.active).toBe(true);
        },
      ),
    );
  });
});
