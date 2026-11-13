import React, { useState } from "react";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { api, CheckoutResponse } from "../services/api";
import CheckoutSummary from "../components/CheckoutSummary";
import CheckoutForm from "../components/CheckoutForm";
import ConfirmationScreen from "../components/ConfirmationScreen";
import { ErrorFallback } from "../components/StateFallbacks";
import { useToast } from "../components/FeedbackToast";

interface CheckoutPageProps {
  onBackToCatalog: () => void;
}

export const CheckoutPage: React.FC<CheckoutPageProps> = ({ onBackToCatalog }) => {
  const { items, clearCart } = useCart();
  const { token } = useAuth();
  const { showToast } = useToast();

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [checkoutResult, setCheckoutResult] = useState<CheckoutResponse | null>(null);

  const handleCheckoutSubmit = async (demonstrationInfo: Record<string, string>) => {
    if (!token) {
      setError("Active session required to proceed to checkout.");
      showToast("Checkout failed: Active session required.", "error");
      return;
    }

    if (items.length === 0) {
      setError("Your shopping cart is empty. Checkout is blocked.");
      showToast("Checkout failed: Cart is empty.", "error");
      return;
    }

    setLoading(true);
    setError(null);

    const apiItems = items.map((item) => ({
      product_id: item.product_id,
      quantity: item.quantity,
    }));

    try {
      const res = await api.checkout(token, apiItems, demonstrationInfo);
      setCheckoutResult(res);
      showToast("Checkout completed successfully!", "success");
      // Note: cart reset is left completely unspecified/flexible in the seed.
      // We choose to clear the local cart upon simulated confirmation to provide a clean state.
      clearCart();
    } catch (err: any) {
      setError(err.message || "Failed to complete simulated checkout.");
      showToast("Checkout failed: Invalid details.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleResetAndStartNew = () => {
    setCheckoutResult(null);
    setError(null);
    onBackToCatalog();
  };

  if (checkoutResult) {
    return <ConfirmationScreen checkoutResult={checkoutResult} onReset={handleResetAndStartNew} />;
  }

  if (items.length === 0) {
    return (
      <div className="checkout-empty-container" data-testid="empty-checkout-state" style={{ padding: "40px", textAlign: "center" }}>
        <h2>Simulated Checkout</h2>
        <p style={{ color: "#666", margin: "15px 0" }}>Your shopping cart is empty. Checkout cannot proceed.</p>
        <button
          onClick={onBackToCatalog}
          style={{ padding: "10px 20px", backgroundColor: "#374151", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}
        >
          Return to Catalog Offering
        </button>
      </div>
    );
  }

  return (
    <div className="checkout-page" data-testid="checkout-page" style={{ maxWidth: "600px", margin: "0 auto", padding: "20px" }}>
      <h2 style={{ fontSize: "22px", fontWeight: "bold", marginBottom: "20px" }}>Simulated Checkout</h2>
      {error && <ErrorFallback message={error} />}
      <CheckoutSummary />
      <CheckoutForm onSubmit={handleCheckoutSubmit} loading={loading} />
      <button
        onClick={onBackToCatalog}
        disabled={loading}
        style={{
          width: "100%",
          padding: "10px",
          backgroundColor: "#9ca3af",
          color: "#111827",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          fontSize: "14px",
          fontWeight: "bold",
          marginTop: "10px",
        }}
      >
        Cancel and Return to Catalog
      </button>
    </div>
  );
};
export default CheckoutPage;
