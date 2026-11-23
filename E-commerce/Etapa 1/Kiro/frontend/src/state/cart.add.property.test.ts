// Property-based test for the pure cart add logic (design: Correctness
// Properties, Testing Strategy — Property-Based Tests). Exercises addItem
// directly over randomly generated starting carts and added products.
//
// Feature: ecommerce-stage1, Property 1: Adding a product makes it present in the cart

import { describe, expect, it } from "vitest";
import fc from "fast-check";

import type { CartItem } from "../types";
import { addItem } from "./cart";

// Arbitrary product ids. Kept non-empty strings so each resolves to a distinct
// identity in the cart.
const productIdArbitrary = fc.string({ minLength: 1, maxLength: 12 });

// An arbitrary starting cart: a list of items keyed by a unique productId, each
// with a positive quantity (>= 1), matching the authoritative CartItem shape.
const startingCartArbitrary: fc.Arbitrary<CartItem[]> = fc.uniqueArray(
  fc.record({
    productId: productIdArbitrary,
    quantity: fc.integer({ min: 1, max: 1000 }),
  }),
  { selector: (item) => item.productId, maxLength: 10 },
);

describe("Property 1: Adding a product makes it present in the cart", () => {
  // Feature: ecommerce-stage1, Property 1: Adding a product makes it present in the cart
  // Validates: Requirements 2.1, 11.6
  it("after addItem the cart contains the product with quantity >= the added quantity", () => {
    fc.assert(
      fc.property(
        fc.record({
          cart: startingCartArbitrary,
          productId: productIdArbitrary,
          quantity: fc.integer({ min: 1, max: 1000 }),
        }),
        ({ cart, productId, quantity }) => {
          const result = addItem(cart, productId, quantity);

          // The resulting cart's contents include an item for that product
          // (R2.1, R11.6).
          const line = result.find((item) => item.productId === productId);
          expect(line).toBeDefined();

          // The added quantity is reflected: whether the product was new or
          // already present, its quantity is at least the amount just added.
          expect(line!.quantity).toBeGreaterThanOrEqual(quantity);
        },
      ),
    );
  });
});
