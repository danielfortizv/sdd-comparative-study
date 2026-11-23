// Pure, testable cart and session logic (design: Shared Journey State, Data
// Models).
//
// The cart is the authoritative client-side list of CartItem held in memory
// only, with no durable persistence across browser closures or separate
// sessions (Requirements 4.1, 4.2, 4.3). These functions operate immutably on
// CartItem[] so React state updates stay predictable and testable.
//
// deriveCartView is the SINGLE source of per-item unit prices, line totals, and
// the accumulated total used by both the Cart and Checkout views (Requirements
// 3.1, 3.2, 11.4, 11.5). Session helpers build an in-memory SessionState that
// never holds a password or credential value (Requirement 7.3).

import type {
  CartItem,
  CartView,
  CartViewLine,
  Product,
  SessionState,
} from "../types";

/**
 * Add a product to the cart. Adding a product already present increments its
 * quantity rather than creating a duplicate line (Requirements 2.1, 2.3,
 * 11.6). Returns a new array; the input is not mutated.
 */
export function addItem(
  cart: CartItem[],
  productId: string,
  quantity: number = 1,
): CartItem[] {
  if (quantity <= 0) {
    return cart;
  }

  const existing = cart.find((item) => item.productId === productId);
  if (existing) {
    return cart.map((item) =>
      item.productId === productId
        ? { ...item, quantity: item.quantity + quantity }
        : item,
    );
  }

  return [...cart, { productId, quantity }];
}

/**
 * Remove a product entirely from the cart (Requirement 3.3). Returns a new
 * array; removing an absent product yields an unchanged copy.
 */
export function removeItem(cart: CartItem[], productId: string): CartItem[] {
  return cart.filter((item) => item.productId !== productId);
}

/**
 * Set the absolute quantity for a product (Requirement 3.2). A quantity of zero
 * or less removes the product from the cart. Setting the quantity of an absent
 * product with a positive value adds it. Unit price is never affected here;
 * totals are derived separately by {@link deriveCartView}.
 */
export function setQuantity(
  cart: CartItem[],
  productId: string,
  quantity: number,
): CartItem[] {
  if (quantity <= 0) {
    return removeItem(cart, productId);
  }

  const existing = cart.find((item) => item.productId === productId);
  if (!existing) {
    return [...cart, { productId, quantity }];
  }

  return cart.map((item) =>
    item.productId === productId ? { ...item, quantity } : item,
  );
}

/**
 * Adjust the quantity for a product by a relative delta (Requirement 3.2). The
 * resulting quantity is clamped so that reaching zero or below removes the
 * product. Adjusting an absent product treats its current quantity as zero.
 */
export function adjustQuantity(
  cart: CartItem[],
  productId: string,
  delta: number,
): CartItem[] {
  const existing = cart.find((item) => item.productId === productId);
  const current = existing ? existing.quantity : 0;
  return setQuantity(cart, productId, current + delta);
}

/** Empty the cart (used on completion / reset-to-new-purchase). */
export function clearCart(): CartItem[] {
  return [];
}

/**
 * Derive the cart view from the authoritative cart and the loaded catalog.
 *
 * For each cart item whose product is present in the catalog, resolves
 * unitPrice = product.price and lineTotal = price * quantity; total is the sum
 * of all line totals. This is the single source of totals shared by the Cart
 * and Checkout views (Requirements 3.1, 3.2, 11.4, 11.5). Items whose product
 * is not in the loaded catalog are skipped gracefully so an unresolved id can
 * never corrupt the total.
 */
export function deriveCartView(cart: CartItem[], catalog: Product[]): CartView {
  const byId = new Map(catalog.map((product) => [product.id, product]));

  const items: CartViewLine[] = [];
  for (const item of cart) {
    const product = byId.get(item.productId);
    if (!product) {
      continue;
    }
    const unitPrice = product.price;
    items.push({
      product,
      quantity: item.quantity,
      unitPrice,
      lineTotal: unitPrice * item.quantity,
    });
  }

  const total = items.reduce((sum, line) => sum + line.lineTotal, 0);

  return { items, total };
}

/**
 * Build an active in-memory session for the given display identity. Holds no
 * password or credential value (Requirement 7.3).
 */
export function activeSession(identity: string): SessionState {
  return { active: true, identity };
}

/** Build an inactive in-memory session (signed out). */
export function inactiveSession(): SessionState {
  return { active: false, identity: null };
}
