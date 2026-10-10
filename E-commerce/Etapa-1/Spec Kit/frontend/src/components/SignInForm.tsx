import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "./FeedbackToast";

export const SignInForm: React.FC<{ onSuccess?: () => void }> = ({ onSuccess }) => {
  const [identifier, setIdentifier] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const { signIn } = useAuth();
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const idVal = identifier.strip ? identifier.strip() : identifier.trim();
    if (!idVal || !password) {
      setError("Please enter your identification and password.");
      showToast("Sign-in failed: Incomplete input.", "error");
      return;
    }

    setLoading(true);
    try {
      await signIn(idVal, password);
      showToast("Welcome! Sign-in successful.", "success");
      setIdentifier("");
      setPassword("");
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      setError(err.message || "Invalid identifier or password.");
      showToast("Sign-in failed: Invalid credentials.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-form-container" data-testid="signin-form">
      <h3 className="form-title">Sign In to Your Account</h3>
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <div className="form-error-message" style={{ color: "#d32f2f", marginBottom: "15px", fontSize: "14px" }}>
            {error}
          </div>
        )}
        <div className="form-group">
          <label htmlFor="signin-identifier" className="form-label">
            Customer Identification (Identifier)
          </label>
          <input
            type="text"
            id="signin-identifier"
            className="form-input"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            disabled={loading}
            placeholder="Enter your registered identifier"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="signin-password" className="form-label">
            Password
          </label>
          <input
            type="password"
            id="signin-password"
            className="form-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            placeholder="Enter your account password"
            required
          />
        </div>
        <button type="submit" className="auth-submit-btn" disabled={loading}>
          {loading ? "Signing In..." : "Sign In"}
        </button>
      </form>
    </div>
  );
};
export default SignInForm;
