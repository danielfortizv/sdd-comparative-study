// Property-based test for catalog-cart product identity consistency (design:
// Correctness Properties, Testing Strategy — Property-Based Tests). Exercises
// deriveCartView directly over randomly generated catalogs and carts to confirm
// the cart reflects the SAME demonstration data shown in the catalog.
//
// Feature: ecommerce-stage1, Property 18: Catalog and cart show consistent product identity

import { describe, expect, it } from "vitest";
import fc from "fast-check";

import type { Product } from "../types";
import { deriveCartView } from "./cart";

// Prices are generated as integer cents and mapped to whole-cent decimal prices
// so the per-line unit price compares exactly against the catalog price without
// any float tolerance.
const priceFromCents = (cents: number): number => cents / 100;

/**
 * Build a catalog of distinct products from a list of unique ids, each with a
 * finite, non-negative integer-cent price. Each product is given distinct
 * demonstration data (name, image, description, price, availability).
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

describe("Property 18: Catalog and cart show consistent product identity", () => {
  // Feature: ecommerce-stage1, Property 18: Catalog and cart show consistent product identity
  // Validates: Requirements 1.5, 11.2
  it("resolved cart line identity, name, and price equal the catalog product's from the same demonstration data", () => {
    fc.assert(
      fc.property(
        // Generate a catalog of distinct ids first, then build the cart from a
        // subset of those same ids so every cart line resolves to a catalog
        // product (the same demonstration data).
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
            }),
          ),
        ({ catalog, cart }) => {
          const view = deriveCartView(cart, catalog);

          // The catalog is the single source of demonstration data; index it by
          // id to compare each resolved cart line against its origin product.
          const catalogById = new Map(catalog.map((p) => [p.id, p]));

          for (const line of view.items) {
            const catalogProduct = catalogById.get(line.product.id);

            // The cart only resolves products that exist in the catalog.
            expect(catalogProduct).toBeDefined();
            const source = catalogProduct as Product;

            // Identity: the resolved line's product id equals the catalog id
            // (R11.2) and the line reflects the same demonstration record
            // (R1.5).
            expect(line.product.id).toBe(source.id);

            // Name: identical to the catalog product's name (R11.2).
            expect(line.product.name).toBe(source.name);

            // Price: the resolved unit price equals the catalog product's price
            // (R11.2); compared on exact integer-cent values.
            expect(line.unitPrice).toBe(source.price);
            expect(line.product.price).toBe(source.price);
          }
        },
      ),
    );
  });
});
