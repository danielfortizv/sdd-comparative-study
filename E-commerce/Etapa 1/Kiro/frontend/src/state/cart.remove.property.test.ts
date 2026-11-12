// Property-based test for cart removal (design: Correctness Properties,
// Testing Strategy — Property-Based Tests). Exercises removeItem directly over
// a randomly generated cart that is guaranteed to contain a target product.
//
// Feature: ecommerce-stage1, Property 3: Removing a product makes it absent from the cart

import { describe, expect, it } from "vitest";
import fc from "fast-check";

import type { CartItem } from "../types";
import { removeItem } from "./cart";

describe("Property 3: Removing a product makes it absent from the cart", () => {
  // Feature: ecommerce-stage1, Property 3: Removing a product makes it absent from the cart
  // Validates: Requirements 3.3
  it("removing a contained product yields a cart with no item having that productId", () => {
    fc.assert(
      fc.property(
        // Generate a cart of distinct product ids plus one target id that is
        // guaranteed to be present among the cart items, so the property always
        // exercises removal of a genuinely contained product (R3.3).
        fc
          .uniqueArray(fc.string({ minLength: 1, maxLength: 8 }), {
            minLength: 1,
            maxLength: 8,
          })
          .chain((ids) =>
            fc.record({
              cart: fc.constant<CartItem[]>(
                ids.map((id) => ({ productId: id, quantity: 1 })),
              ).chain((baseCart) =>
                // Assign each contained product an arbitrary positive quantity.
                fc
                  .tuple(
                    ...baseCart.map(() => fc.integer({ min: 1, max: 1000 })),
                  )
                  .map((quantities) =>
                    baseCart.map((item, index) => ({
                      ...item,
                      quantity: quantities[index],
                    })),
                  ),
              ),
              // The target is any id drawn from the ids actually in the cart.
              targetId: fc.constantFrom(...ids),
            }),
          ),
        ({ cart, targetId }) => {
          // Precondition: the generated cart contains the target product.
          expect(cart.some((item) => item.productId === targetId)).toBe(true);

          const result = removeItem(cart, targetId);

          // The target product is absent from the resulting cart (R3.3).
          expect(result.some((item) => item.productId === targetId)).toBe(
            false,
          );

          // Every other product that was present remains present, so removal
          // affects only the targeted product.
          const expectedRemaining = cart
            .filter((item) => item.productId !== targetId)
            .map((item) => item.productId)
            .sort();
          const actualRemaining = result
            .map((item) => item.productId)
            .sort();
          expect(actualRemaining).toEqual(expectedRemaining);
        },
      ),
    );
  });
});
