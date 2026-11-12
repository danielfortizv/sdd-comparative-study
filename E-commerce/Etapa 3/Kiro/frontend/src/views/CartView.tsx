// Cart view (design: Frontend Components — Cart).
//
// Renders the local, in-memory cart from the single source of totals exposed by
// the shared journey state. For each contained product it shows the name,
// quantity, unit price, and line total, plus the accumulated purchase total
// (Requirement 3.1). Quantity adjust controls call adjustQuantity so the
// quantity and total update immediately while the unit price stays consistent
// (Requirement 3.2). A remove control removes a product and surfaces a visible
// removal confirmation (Requirement 3.3). When the cart holds no products an
// empty-state indication is shown (Requirement 3.4). The cart updates its
// displayed contents automatically from state when a product is added — no
// extra user action is needed (Requirement 2.3) — and a visible add
// confirmation appears when the cart gains an item (Requirements 2.1, 2.2,
// 11.6). Cart contents are retained for viewing throughout the Active_Journey
// because they live in the shared journey state (Requirement 3.5).
//
// Confirmations are announced through an aria-live region so they are visible
// and accessible (Requirement 13.2).

import { useEffect, useRef, useState } from "react";

import { useJourney } from "../state/JourneyState";

/** Format a monetary value consistently across the cart view. */
function formatCurrency(value: number): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
  });
}

/** Total number of individual units currently in the cart. */
function totalUnits(items: { quantity: number }[]): number {
  return items.reduce((sum, line) => sum + line.quantity, 0);
}

export function CartView() {
  const { cartView, adjustQuantity, removeFromCart } = useJourney();
  const { items, total } = cartView;

  // Confirmation messages announced via an aria-live region. The add
  // confirmation is driven by observing the cart gaining units (adds originate
  // in the Catalog but are reflected here automatically from shared state).
  const [confirmation, setConfirmation] = useState<string>("");
  const previousUnits = useRef<number>(totalUnits(items));

  useEffect(() => {
    const current = totalUnits(items);
    if (current > previousUnits.current) {
      setConfirmation("Product added to your cart.");
    }
    previousUnits.current = current;
  }, [items]);

  const handleRemove = (productId: string, name: string) => {
    removeFromCart(productId);
    setConfirmation(`${name} was removed from your cart.`);
  };

  return (
    <section aria-labelledby="cart-heading">
      <h2 id="cart-heading">Cart</h2>

      {/* Visible, accessible confirmation region for add/remove feedback
          (Requirements 2.2, 3.3, 13.2). */}
      <p role="status" aria-live="polite" data-testid="cart-confirmation">
        {confirmation}
      </p>

      {items.length === 0 ? (
        <p data-testid="cart-empty-state">
          Your cart is empty. Browse the catalog to add products.
        </p>
      ) : (
        <>
          <ul aria-label="Cart items">
            {items.map((line) => (
              <li key={line.product.id} data-testid={`cart-item-${line.product.id}`}>
                <span data-testid="cart-item-name">{line.product.name}</span>
                <span data-testid="cart-item-unit-price">
                  Unit price: {formatCurrency(line.unitPrice)}
                </span>
                <span
                  data-testid="cart-item-quantity"
                  aria-label={`Quantity of ${line.product.name}`}
                >
                  Quantity: {line.quantity}
                </span>
                <span data-testid="cart-item-line-total">
                  Line total: {formatCurrency(line.lineTotal)}
                </span>
                <button
                  type="button"
                  aria-label={`Increase quantity of ${line.product.name}`}
                  onClick={() => adjustQuantity(line.product.id, 1)}
                >
                  Increase
                </button>
                <button
                  type="button"
                  aria-label={`Decrease quantity of ${line.product.name}`}
                  onClick={() => adjustQuantity(line.product.id, -1)}
                >
                  Decrease
                </button>
                <button
                  type="button"
                  aria-label={`Remove ${line.product.name} from cart`}
                  onClick={() => handleRemove(line.product.id, line.product.name)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>

          <p data-testid="cart-total">Total: {formatCurrency(total)}</p>
        </>
      )}
    </section>
  );
}
