import React from "react";
import { CheckoutResponse } from "../services/api";

export interface ConfirmationScreenProps {
  checkoutResult: CheckoutResponse;
  onReset: () => void;
}

export const ConfirmationScreen: React.FC<ConfirmationScreenProps> = ({ checkoutResult, onReset }) => {
  return (
    <div className="confirmation-container" data-testid="confirmation-panel" style={{ padding: "30px", border: "1px solid #d1fae5", backgroundColor: "#ecfdf5", borderRadius: "4px", margin: "20px 0" }}>
      <div style={{ textAlign: "center", marginBottom: "25px" }}>
        <span style={{ fontSize: "40px" }}>✓</span>
        <h2 style={{ color: "#065f46", fontSize: "20px", fontWeight: "bold", marginTop: "10px" }}>Simulated Purchase Confirmed!</h2>
        <p style={{ color: "#047857", fontSize: "14px", marginTop: "5px" }}>{checkoutResult.message}</p>
      </div>

      <div style={{ backgroundColor: "#fff", padding: "20px", borderRadius: "4px", border: "1px solid #e5e7eb", marginBottom: "25px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: "bold", borderBottom: "1px solid #f3f4f6", paddingBottom: "10px", marginBottom: "15px", color: "#111827" }}>
          Simulated Purchase Summary
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {checkoutResult.purchase_summary.items.map((item) => (
            <div key={item.product_id} style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", color: "#374151" }}>
              <span>
                <strong>{item.name}</strong> x {item.quantity}
              </span>
              <span>${item.subtotal.toFixed(2)}</span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid #f3f4f6", paddingTop: "15px", marginTop: "15px", fontSize: "15px", fontWeight: "bold", color: "#111827" }}>
          <span>Simulated Grand Total:</span>
          <span>${checkoutResult.purchase_summary.accumulated_total.toFixed(2)}</span>
        </div>
      </div>

      <div style={{ padding: "15px", backgroundColor: "#fef3c7", border: "1px solid #fde68a", borderRadius: "4px", color: "#92400e", fontSize: "13px", marginBottom: "25px", lineHeight: "1.5" }}>
        <strong>Fictitious Gateway Disclaimer:</strong> No real payment gateway was contacted, no actual credit card was requested, and no charge has been made. This is strictly an academic demonstration online store.
      </div>

      <button
        onClick={onReset}
        style={{
          width: "100%",
          padding: "10px",
          backgroundColor: "#059669",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          fontSize: "14px",
          fontWeight: "bold",
        }}
      >
        Start New Simulated Purchase Journey
      </button>
    </div>
  );
};
export default ConfirmationScreen;
