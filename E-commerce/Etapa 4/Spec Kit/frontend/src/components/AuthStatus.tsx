import React from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "./FeedbackToast";

export const AuthStatus: React.FC = () => {
  const { isAuthenticated, identifier, signOut } = useAuth();
  const { showToast } = useToast();

  const handleSignOut = async () => {
    await signOut();
    showToast("Signed out successfully. Your cart selection has been preserved.", "info");
  };

  if (!isAuthenticated) {
    return (
      <div className="auth-status-container" data-testid="unauthenticated-status">
        <span className="status-label">Guest Visitor</span>
      </div>
    );
  }

  return (
    <div className="auth-status-container" data-testid="authenticated-status">
      <span className="status-label">Active Session: <strong>{identifier}</strong></span>
      <button
        className="sign-out-btn"
        onClick={handleSignOut}
        aria-label="Sign Out"
        style={{
          marginLeft: "15px",
          padding: "6px 12px",
          backgroundColor: "#374151",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          fontSize: "12px",
          fontWeight: 500,
        }}
      >
        Sign Out
      </button>
    </div>
  );
};
export default AuthStatus;
