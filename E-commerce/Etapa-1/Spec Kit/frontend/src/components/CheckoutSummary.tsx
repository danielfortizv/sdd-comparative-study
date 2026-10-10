import React from "react";
import { useCart } from "../context/CartContext";

export const CheckoutSummary: React.FC = () => {
  const { items, accumulated_total } = useCart();

  return (
    <div className="checkout-summary-container" data-testid="checkout-summary">
      <h3 className="summary-title" style={{ borderBottom: "2px solid #e5e7eb", paddingBottom: "10px", marginBottom: "15px" }}>
        Pre-Confirmation Purchase Summary
      </h3>
      <div className="summary-items" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {items.map((item) => (
          <div
            key={item.product_id}
            className="summary-item"
            data-testid="summary-item"
            style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", color: "#374151" }}
          >
            <span>
              <strong>{item.name}</strong> x {item.quantity}
            </span>
            <span style={{ fontWeight: 500 }}>${item.subtotal.toFixed(2)}</span>
          </div>
        ))}
      </div>
      <div
        className="summary-total-row"
        style={{
          display: "flex",
          justify_content: "space-between",
          borderTop: "2px solid #e5e7eb",
          paddingTop: "15px",
          marginTop: "15px",
          fontSize: "16px",
          fontWeight: "bold",
          color: "#111827",
        }}
      >
        <span>Accumulated Purchase Total:</span>
        <span data-testid="checkout-total">${accumulated_total.toFixed(2)}</span>
      </div>
    </div>
  );
};
export default CheckoutSummary;
