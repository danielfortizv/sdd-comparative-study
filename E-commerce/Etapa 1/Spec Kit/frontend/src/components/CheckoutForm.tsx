import React, { useState } from "react";

export interface CheckoutFormProps {
  onSubmit: (info: Record<string, string>) => void;
  loading: boolean;
}

export const CheckoutForm: React.FC<CheckoutFormProps> = ({ onSubmit, loading }) => {
  // Use generic opaque keys to collect minimal demonstration info
  const [fieldA, setFieldA] = useState<string>("");
  const [fieldB, setFieldB] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const valA = fieldA.trim();
    const valB = fieldB.trim();

    if (!valA || !valB) {
      setError("Please fill in the minimum requested demonstration information.");
      return;
    }

    // Submit minimal opaque dictionary
    onSubmit({
      demo_info_field_a: valA,
      demo_info_field_b: valB,
    });
  };

  return (
    <div className="checkout-form-container" data-testid="checkout-form" style={{ marginTop: "20px" }}>
      <h3 className="form-title" style={{ fontSize: "16px", marginBottom: "15px" }}>Simulated Shipment Information</h3>
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <div className="form-error-message" style={{ color: "#d32f2f", marginBottom: "15px", fontSize: "14px" }}>
            {error}
          </div>
        )}
        <div className="form-group" style={{ marginBottom: "15px" }}>
          <label htmlFor="checkout-field-a" className="form-label" style={{ display: "block", marginBottom: "5px", fontSize: "14px", fontWeight: 500 }}>
            Demonstration Reference Detail A (e.g., Name / Identifier)
          </label>
          <input
            type="text"
            id="checkout-field-a"
            className="form-input"
            value={fieldA}
            onChange={(e) => setFieldA(e.target.value)}
            disabled={loading}
            placeholder="Provide detail A reference"
            required
            style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px" }}
          />
        </div>
        <div className="form-group" style={{ marginBottom: "20px" }}>
          <label htmlFor="checkout-field-b" className="form-label" style={{ display: "block", marginBottom: "5px", fontSize: "14px", fontWeight: 500 }}>
            Demonstration Reference Detail B (e.g., Contact Reference)
          </label>
          <input
            type="text"
            id="checkout-field-b"
            className="form-input"
            value={fieldB}
            onChange={(e) => setFieldB(e.target.value)}
            disabled={loading}
            placeholder="Provide detail B reference"
            required
            style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px" }}
          />
        </div>
        <button
          type="submit"
          className="checkout-submit-btn"
          disabled={loading}
          style={{
            width: "100%",
            padding: "10px",
            backgroundColor: "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "15px",
            fontWeight: "bold",
          }}
        >
          {loading ? "Confirming simulated checkout..." : "Confirm Simulated Purchase"}
        </button>
      </form>
    </div>
  );
};
export default CheckoutForm;
