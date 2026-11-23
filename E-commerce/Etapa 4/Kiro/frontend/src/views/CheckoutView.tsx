// Checkout view (design: Frontend Components — Checkout).
//
// Presents the pre-confirmation summary of products, quantities, and total from
// the single source of totals (R9.1); requests no demonstration information
// beyond what is strictly necessary and provides neither an address book nor
// saved-address selection (R9.2, R9.3, R9.4); and prevents proceeding when the
// cart is empty (R9.5).
//
// Before completion the person must be identified. When no session is active
// the view surfaces a sign-in option and a register option and blocks
// completion until the person is identified (R8.1, R8.2). Because the cart
// lives in the shared journey state, items are preserved across sign-in and
// registration automatically — the gate never clears the cart (R8.3, R8.4).
//
// A visible fictitious-payment notice states that no charge is made and no real
// payment gateway is contacted (R10.1). On a successful simulated purchase the
// view shows an unambiguous confirmation with a purchased-items summary (R10.2)
// and visible finished feedback (R10.4), then offers a return to a
// comprehensible new-purchase state (R10.3).
//
// Confirmations and errors are announced through aria-live regions and all
// controls are labeled (R13.2).

import { useState } from "react";

import { ApiError, apiClient } from "../api/client";
import { useJourney } from "../state/JourneyState";
import type { CheckoutConfirmation } from "../types";

/** Format a monetary value consistently across the checkout view. */
function formatCurrency(value: number): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
  });
}

export function CheckoutView() {
  const { cart, cartView, session, clearCart } = useJourney();
  const { items, total } = cartView;

  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<CheckoutConfirmation | null>(
    null,
  );

  const cartEmpty = items.length === 0;
  const identified = session.active && session.identity !== null;
  // Completion is only valid for an identified person with a non-empty cart.
  const canComplete = identified && !cartEmpty && !pending;

  async function handleComplete() {
    setError(null);
    setPending(true);
    try {
      const result = await apiClient.confirmCheckout({
        items: cart.map((item) => ({
          productId: item.productId,
          quantity: item.quantity,
        })),
      });
      setConfirmation(result);
    } catch (err) {
      // Request-failure state (R12.4): always describe what the person can do
      // next. When the backend supplies a specific reason, keep it but append a
      // consistent next-step hint so the message is actionable.
      const NEXT_STEP = "Please try again.";
      if (err instanceof ApiError && err.message) {
        const reason = err.message.trim();
        setError(/try again/i.test(reason) ? reason : `${reason} ${NEXT_STEP}`);
      } else {
        setError(`The purchase could not be completed. ${NEXT_STEP}`);
      }
    } finally {
      setPending(false);
    }
  }

  function handleStartNewPurchase() {
    // Return to a comprehensible state from which a new purchase can start
    // (R10.3): empty the cart and reset local completion state.
    clearCart();
    setConfirmation(null);
    setError(null);
  }

  // --- Completed state: unambiguous confirmation + purchased-items summary ---
  if (confirmation !== null) {
    return (
      <section aria-labelledby="checkout-heading">
        <h2 id="checkout-heading">Checkout</h2>

        {/* Visible finished feedback + unambiguous confirmation (R10.2, R10.4). */}
        <div role="status" aria-live="polite" data-testid="checkout-confirmation">
          <p data-testid="checkout-finished">
            Purchase complete. Your simulated purchase has finished.
          </p>
          <p>
            This was a simulated purchase. No charge was made and no real
            payment gateway was contacted.
          </p>
        </div>

        <h3>Purchased items</h3>
        <ul aria-label="Purchased items">
          {confirmation.items.map((line) => (
            <li
              key={line.productId}
              data-testid={`checkout-purchased-${line.productId}`}
            >
              <span data-testid="purchased-name">{line.name}</span>
              <span data-testid="purchased-quantity">
                Quantity: {line.quantity}
              </span>
              <span data-testid="purchased-unit-price">
                Unit price: {formatCurrency(line.unitPrice)}
              </span>
              <span data-testid="purchased-line-total">
                Line total: {formatCurrency(line.lineTotal)}
              </span>
            </li>
          ))}
        </ul>
        <p data-testid="checkout-confirmation-total">
          Total: {formatCurrency(confirmation.total)}
        </p>

        <button
          type="button"
          onClick={handleStartNewPurchase}
          data-testid="start-new-purchase"
        >
          Start a new purchase
        </button>
      </section>
    );
  }

  return (
    <section aria-labelledby="checkout-heading">
      <h2 id="checkout-heading">Checkout</h2>

      {/* Fictitious-payment notice shown at all times before completion (R10.1). */}
      <p data-testid="fictitious-payment-notice">
        This is a simulated checkout. No charge is made and no real payment
        gateway is contacted.
      </p>

      {/* Request-failure feedback (announced assertively). */}
      {error !== null && (
        <p role="alert" aria-live="assertive" data-testid="checkout-error">
          {error}
        </p>
      )}

      {cartEmpty ? (
        // Empty-cart guard: no valid purchase can proceed (R9.5).
        <p data-testid="checkout-empty-state">
          Your cart is empty. Add products from the catalog before checking out.
        </p>
      ) : (
        <>
          {/* Pre-confirmation summary: each product, its quantity, and the
              total from the single source of totals (R9.1). */}
          <h3>Order summary</h3>
          <ul aria-label="Checkout summary">
            {items.map((line) => (
              <li
                key={line.product.id}
                data-testid={`checkout-item-${line.product.id}`}
              >
                <span data-testid="checkout-item-name">{line.product.name}</span>
                <span data-testid="checkout-item-quantity">
                  Quantity: {line.quantity}
                </span>
                <span data-testid="checkout-item-unit-price">
                  Unit price: {formatCurrency(line.unitPrice)}
                </span>
                <span data-testid="checkout-item-line-total">
                  Line total: {formatCurrency(line.lineTotal)}
                </span>
              </li>
            ))}
          </ul>
          <p data-testid="checkout-total">Total: {formatCurrency(total)}</p>

          {identified ? (
            <>
              <button
                type="button"
                onClick={handleComplete}
                disabled={!canComplete}
                data-testid="complete-purchase"
              >
                {pending ? "Completing purchase…" : "Complete purchase"}
              </button>
              {/* Visible loading indicator while the request is in flight
                  (R12.2). */}
              {pending && (
                <p role="status" aria-live="polite" data-testid="checkout-loading">
                  Completing your purchase… Please wait.
                </p>
              )}
            </>
          ) : (
            // Identification gate: block completion and present sign-in and
            // register options directing the person to the Account view
            // (R8.1, R8.2). The cart is preserved automatically (R8.3, R8.4).
            <div data-testid="identification-gate">
              <p data-testid="identification-required">
                You need to be identified to complete your purchase. Your cart is
                kept while you sign in or register.
              </p>
              <p>
                <a href="#account" data-testid="checkout-signin-option">
                  Sign in to your account
                </a>
              </p>
              <p>
                <a href="#account" data-testid="checkout-register-option">
                  Register a new account
                </a>
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
