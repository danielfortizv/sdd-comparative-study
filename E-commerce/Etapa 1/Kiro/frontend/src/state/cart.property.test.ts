// Property-based test for the pure cart math (design: Correctness Properties,
// Testing Strategy — Property-Based Tests). Exercises deriveCartView directly
// over randomly generated catalogs and carts.
//
// Feature: ecommerce-stage1, Property 2: Cart total equals the sum of line totals

import { describe, expect, it } from "vitest";
import fc from "fast-check";

import type { CartItem, Product } from "../types";
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

describe("Property 2: Cart total equals the sum of line totals", () => {
  // Feature: ecommerce-stage1, Property 2: Cart total equals the sum of line totals
  // Validates: Requirements 3.1, 3.2
  it("total equals sum of unitPrice*quantity and unit price is unaffected by quantity", () => {
    fc.assert(
      fc.property(
        // Generate a catalog of distinct ids first, then build the cart from
        // those same ids so every cart line resolves to a catalog product.
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
                { selector: (item) => item.productId, maxLength: ids.length },
              ),
              // An alternate positive quantity used to re-derive one item and
              // confirm the unit price does not depend on quantity.
              altQuantity: fc.integer({ min: 1, max: 1000 }),
            }),
          ),
        ({ catalog, cart, altQuantity }) => {
          const view = deriveCartView(cart, catalog);

          // The accumulated total equals the sum of unitPrice * quantity across
          // all lines. Compared in integer cents to stay exact (R3.1).
          const expectedTotalCents = view.items.reduce(
            (sum, line) => sum + toCents(line.unitPrice) * line.quantity,
            0,
          );
          expect(toCents(view.total)).toBe(expectedTotalCents);

          // Each line's unit price equals its product's price and each line
          // total equals unitPrice * quantity (R3.1, R3.2).
          const priceById = new Map(catalog.map((p) => [p.id, p.price]));
          for (const line of view.items) {
            expect(line.unitPrice).toBe(priceById.get(line.product.id));
            expect(toCents(line.lineTotal)).toBe(
              toCents(line.unitPrice) * line.quantity,
            );
          }

          // Unit price is unchanged by quantity changes: re-deriving the same
          // product with a different quantity yields the same unit price (R3.2).
          for (const line of view.items) {
            const reDerived = deriveCartView(
              [{ productId: line.product.id, quantity: altQuantity } as CartItem],
              catalog,
            );
            expect(reDerived.items[0].unitPrice).toBe(line.unitPrice);
          }
        },
      ),
    );
  });
});
