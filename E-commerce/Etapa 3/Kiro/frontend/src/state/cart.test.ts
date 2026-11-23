// Example-based unit tests for the pure cart and session logic (design:
// Testing Strategy — Unit and Example Tests). The fast-check property tests for
// cart math and preservation (Properties 2 and 4) are separate tasks (7.3/7.4);
// these tests cover specific examples and edge cases.

import { describe, expect, it } from "vitest";

import type { CartItem, Product } from "../types";
import {
  activeSession,
  addItem,
  adjustQuantity,
  clearCart,
  deriveCartView,
  inactiveSession,
  removeItem,
  setQuantity,
} from "./cart";

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

describe("addItem", () => {
  it("adds a new product with the given quantity", () => {
    const result = addItem([], "p1", 2);
    expect(result).toEqual([{ productId: "p1", quantity: 2 }]);
  });

  it("defaults the quantity to 1 when omitted", () => {
    expect(addItem([], "p1")).toEqual([{ productId: "p1", quantity: 1 }]);
  });

  it("increments the quantity of an existing product", () => {
    const start: CartItem[] = [{ productId: "p1", quantity: 1 }];
    expect(addItem(start, "p1", 2)).toEqual([{ productId: "p1", quantity: 3 }]);
  });

  it("does not mutate the input array", () => {
    const start: CartItem[] = [{ productId: "p1", quantity: 1 }];
    const snapshot = structuredClone(start);
    addItem(start, "p1", 2);
    expect(start).toEqual(snapshot);
  });

  it("ignores non-positive quantities", () => {
    const start: CartItem[] = [{ productId: "p1", quantity: 1 }];
    expect(addItem(start, "p1", 0)).toBe(start);
    expect(addItem(start, "p2", -3)).toBe(start);
  });
});

describe("removeItem", () => {
  it("removes a contained product", () => {
    const start: CartItem[] = [
      { productId: "p1", quantity: 1 },
      { productId: "p2", quantity: 2 },
    ];
    expect(removeItem(start, "p1")).toEqual([{ productId: "p2", quantity: 2 }]);
  });

  it("leaves the cart unchanged when the product is absent", () => {
    const start: CartItem[] = [{ productId: "p1", quantity: 1 }];
    expect(removeItem(start, "p9")).toEqual(start);
  });
});

describe("setQuantity", () => {
  it("sets the absolute quantity for an existing product", () => {
    const start: CartItem[] = [{ productId: "p1", quantity: 1 }];
    expect(setQuantity(start, "p1", 5)).toEqual([
      { productId: "p1", quantity: 5 },
    ]);
  });

  it("adds the product when it is absent and the quantity is positive", () => {
    expect(setQuantity([], "p1", 3)).toEqual([{ productId: "p1", quantity: 3 }]);
  });

  it("removes the product when the quantity drops to zero or below", () => {
    const start: CartItem[] = [{ productId: "p1", quantity: 2 }];
    expect(setQuantity(start, "p1", 0)).toEqual([]);
    expect(setQuantity(start, "p1", -1)).toEqual([]);
  });
});

describe("adjustQuantity", () => {
  it("increments by a positive delta", () => {
    const start: CartItem[] = [{ productId: "p1", quantity: 2 }];
    expect(adjustQuantity(start, "p1", 3)).toEqual([
      { productId: "p1", quantity: 5 },
    ]);
  });

  it("removes the product when the delta reduces it to zero", () => {
    const start: CartItem[] = [{ productId: "p1", quantity: 2 }];
    expect(adjustQuantity(start, "p1", -2)).toEqual([]);
  });

  it("treats an absent product's current quantity as zero", () => {
    expect(adjustQuantity([], "p1", 2)).toEqual([
      { productId: "p1", quantity: 2 },
    ]);
  });
});

describe("clearCart", () => {
  it("returns an empty cart", () => {
    expect(clearCart()).toEqual([]);
  });
});

describe("deriveCartView", () => {
  it("resolves unit price, line total, and the accumulated total", () => {
    const cart: CartItem[] = [
      { productId: "p1", quantity: 2 },
      { productId: "p2", quantity: 3 },
    ];
    const view = deriveCartView(cart, PRODUCTS);

    expect(view.items).toEqual([
      {
        product: PRODUCTS[0],
        quantity: 2,
        unitPrice: 4.5,
        lineTotal: 9,
      },
      {
        product: PRODUCTS[1],
        quantity: 3,
        unitPrice: 1.25,
        lineTotal: 3.75,
      },
    ]);
    expect(view.total).toBe(12.75);
  });

  it("has a total equal to the sum of line totals", () => {
    const cart: CartItem[] = [
      { productId: "p1", quantity: 4 },
      { productId: "p2", quantity: 1 },
    ];
    const view = deriveCartView(cart, PRODUCTS);
    const sum = view.items.reduce((acc, line) => acc + line.lineTotal, 0);
    expect(view.total).toBe(sum);
  });

  it("keeps unit price unaffected by quantity", () => {
    const low = deriveCartView([{ productId: "p1", quantity: 1 }], PRODUCTS);
    const high = deriveCartView([{ productId: "p1", quantity: 99 }], PRODUCTS);
    expect(low.items[0].unitPrice).toBe(high.items[0].unitPrice);
    expect(high.items[0].unitPrice).toBe(PRODUCTS[0].price);
  });

  it("skips items whose product is not in the loaded catalog", () => {
    const cart: CartItem[] = [
      { productId: "p1", quantity: 2 },
      { productId: "missing", quantity: 5 },
    ];
    const view = deriveCartView(cart, PRODUCTS);
    expect(view.items).toHaveLength(1);
    expect(view.items[0].product.id).toBe("p1");
    expect(view.total).toBe(9);
  });

  it("returns an empty view for an empty cart", () => {
    expect(deriveCartView([], PRODUCTS)).toEqual({ items: [], total: 0 });
  });
});

describe("session helpers", () => {
  it("builds an active session carrying only the display identity", () => {
    const session = activeSession("ada");
    expect(session).toEqual({ active: true, identity: "ada" });
    expect(Object.keys(session).sort()).toEqual(["active", "identity"]);
  });

  it("builds an inactive session with no identity", () => {
    expect(inactiveSession()).toEqual({ active: false, identity: null });
  });
});
