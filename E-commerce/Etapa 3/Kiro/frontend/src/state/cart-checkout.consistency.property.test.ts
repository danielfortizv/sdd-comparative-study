// Property-based test for cart/checkout consistency (design: Correctness
// Properties, Testing Strategy — Property-Based Tests).
//
// The Cart and Checkout views both derive their displayed summary from the SAME
// source: deriveCartView(cart, catalog). The Checkout pre-confirmation summary
// is built from this same cartView, so consistency can be proven at the
// derivation level: for any non-empty cart over a generated catalog, the view
// used by Cart and the view used by Checkout (both deriveCartView of the same
// cart + catalog) agree on product identities, names, prices, per-product
// quantities, and the overall total.
//
// Feature: ecommerce-stage1, Property 19: Cart and checkout are consistent

import { describe, expect, it } from "vitest";
import fc from "fast-check";

import type { Product } from "../types";
import { deriveCartView } from "./cart";

// Prices are generated as integer cents and mapped to whole-cent decimal prices
// so that unitPrice * quantity and the accumulated sum are exact integers in
// cents, letting the property assert equality without any float tolerance.
const priceFromCents = (cents: number): number => cents / 100;
const toCents = (price: number): number => Math.round(price * 100);

/**
 * Build a catalog of distinct products from a list of unique ids, each with a
 * finite, non-negative integer-cent price.
 */
const catalogArbitrary = (ids: string[]): fc.Arbitrary<Product[]> =>
  fc
    .tuple(
      ...ids.map(() =>
        fc.record({
          name: fc.string(),
          imageUrl: fc.webUrl(),
          description: fc.string(),
          priceCents: fc.integer({ min: 0, max: 1_000_000 }),
          available: fc.boolean(),
        }),
      ),
    )
    .map((records) =>
      records.map((record, index) => ({
        id: ids[index],
        name: record.name,
        imageUrl: record.imageUrl,
        description: record.description,
        price: priceFromCents(record.priceCents),
        available: record.available,
      })),
    );

describe("Property 19: Cart and checkout are consistent", () => {
  // Feature: ecommerce-stage1, Property 19: Cart and checkout are consistent
  // Validates: Requirements 9.1, 11.3, 11.4, 11.5
  it("checkout summary lists the same identities, names, prices, quantities, and total as the cart", () => {
    fc.assert(
      fc.property(
        // Generate a catalog of distinct ids first, then build a NON-EMPTY cart
        // from those same ids so every cart line resolves to a catalog product.
        fc
          .uniqueArray(fc.string({ minLength: 1, maxLength: 8 }), {
            minLength: 1,
            maxLength: 8,
          })
          .chain((ids) =>
            fc.record({
              catalog: catalogArbitrary(ids),
              cart: fc.uniqueArray(
                fc.record({
                  productId: fc.constantFrom(...ids),
                  quantity: fc.integer({ min: 1, max: 1000 }),
                }),
                {
                  selector: (item) => item.productId,
                  minLength: 1,
                  maxLength: ids.length,
                },
              ),
            }),
          ),
        ({ catalog, cart }) => {
          // Both views are the same pure function of the same inputs: the view
          // the Cart renders and the view the Checkout pre-confirmation summary
          // is built from.
          const cartView = deriveCartView(cart, catalog);
          const checkoutView = deriveCartView(cart, catalog);

          // Non-empty cart over the generated catalog yields a non-empty view.
          expect(cartView.items.length).toBe(cart.length);

          // The two views agree on their line count.
          expect(checkoutView.items.length).toBe(cartView.items.length);

          const catalogById = new Map(catalog.map((p) => [p.id, p]));
          const cartQuantityById = new Map(
            cart.map((item) => [item.productId, item.quantity]),
          );

          // Line-by-line the Cart view and the Checkout view agree on product
          // identity, name, unit price, and quantity; and each matches the
          // catalog product and the per-product quantity the cart specifies
          // (R9.1, R11.3, R11.4, R11.5).
          for (let i = 0; i < cartView.items.length; i++) {
            const cartLine = cartView.items[i];
            const checkoutLine = checkoutView.items[i];

            // Cart and Checkout agree on this line.
            expect(checkoutLine.product.id).toBe(cartLine.product.id);
            expect(checkoutLine.product.name).toBe(cartLine.product.name);
            expect(checkoutLine.unitPrice).toBe(cartLine.unitPrice);
            expect(checkoutLine.quantity).toBe(cartLine.quantity);

            // Identity, name, and price equal the catalog product.
            const product = catalogById.get(cartLine.product.id)!;
            expect(cartLine.product.id).toBe(product.id);
            expect(cartLine.product.name).toBe(product.name);
            expect(cartLine.unitPrice).toBe(product.price);

            // Per-product quantity equals what the cart specifies.
            expect(cartLine.quantity).toBe(
              cartQuantityById.get(cartLine.product.id),
            );
          }

          // The overall total is identical between the two views and equals the
          // sum of unitPrice * quantity the cart items specify. Compared in
          // integer cents to stay exact (R11.5).
          const expectedTotalCents = cartView.items.reduce(
            (sum, line) =>
              sum +
              toCents(catalogById.get(line.product.id)!.price) *
                cartQuantityById.get(line.product.id)!,
            0,
          );
          expect(toCents(cartView.total)).toBe(expectedTotalCents);
          expect(toCents(checkoutView.total)).toBe(toCents(cartView.total));
        },
      ),
    );
  });
});
