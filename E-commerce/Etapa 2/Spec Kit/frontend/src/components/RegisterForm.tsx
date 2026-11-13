import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "./FeedbackToast";

export const RegisterForm: React.FC<{ onSuccess?: () => void }> = ({ onSuccess }) => {
  const [identifier, setIdentifier] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const { register } = useAuth();
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const idVal = identifier.trim();
    if (!idVal || !password) {
      setError("Please fill in all expected information.");
      showToast("Registration failed: Incomplete input.", "error");
      return;
    }

    setLoading(true);
    try {
      await register(idVal, password);
      showToast("Account successfully registered!", "success");
      setIdentifier("");
      setPassword("");
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      setError(err.message || "Registration failed. Please verify your details.");
      showToast("Registration failed: Invalid input details.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-form-container" data-testid="register-form">
      <h3 className="form-title">Create a Customer Account</h3>
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <div className="form-error-message" style={{ color: "#d32f2f", marginBottom: "15px", fontSize: "14px" }}>
            {error}
          </div>
        )}
        <div className="form-group">
          <label htmlFor="register-identifier" className="form-label">
            Customer Identification (Identifier)
          </label>
          <input
            type="text"
            id="register-identifier"
            className="form-input"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            disabled={loading}
            placeholder="Enter your customer identifier"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="register-password" className="form-label">
            Secure Password
          </label>
          <input
            type="password"
            id="register-password"
            className="form-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            placeholder="Enter a secure password"
            required
          />
        </div>
        <button type="submit" className="auth-submit-btn" disabled={loading}>
          {loading ? "Registering..." : "Register Account"}
        </button>
      </form>
    </div>
  );
};
export default RegisterForm;
