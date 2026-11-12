import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { CartProvider, useCart } from "./context/CartContext";
import { ToastProvider, useToast } from "./components/FeedbackToast";
import CatalogPage from "./pages/CatalogPage";
import CheckoutPage from "./pages/CheckoutPage";
import AuthStatus from "./components/AuthStatus";
import RegisterForm from "./components/RegisterForm";
import SignInForm from "./components/SignInForm";
import ModeratorDashboard from "./components/ModeratorDashboard";

const AppContent: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<"catalog" | "checkout" | "moderation">("catalog");
  const [authView, setAuthView] = useState<"none" | "signin" | "register">("none");

  const { isAuthenticated, identifier } = useAuth();
  const { items } = useCart();
  const { showToast } = useToast();

  useEffect(() => {
    if (identifier !== "moderator" && currentPage === "moderation") {
      setCurrentPage("catalog");
    }
  }, [identifier, currentPage]);

  const handleProceedToCheckout = () => {
    if (items.length === 0) {
      showToast("Your shopping cart is empty.", "error");
      return;
    }

    if (isAuthenticated) {
      setCurrentPage("checkout");
      setAuthView("none");
    } else {
      // Guide unauthenticated visitor to register or sign-in without losing the cart
      showToast("Authentication is required to proceed. Please sign in or register.", "info");
      setAuthView("signin");
    }
  };

  const handleAuthSuccess = () => {
    setAuthView("none");
    if (items.length > 0) {
      setCurrentPage("checkout");
    }
  };

  return (
    <div className="app-layout">
      {/* Header View Status Indicators */}
      <header className="app-header">
        <div className="header-inner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "15px" }}>
          <h1 className="header-title" onClick={() => setCurrentPage("catalog")} style={{ cursor: "pointer", margin: 0 }}>
            🛒 Demonstration Store
          </h1>

          {/* Navigation for Moderator */}
          {identifier === "moderator" && (
            <nav className="header-nav" style={{ display: "flex", gap: "10px" }}>
              <button
                onClick={() => setCurrentPage("catalog")}
                style={{
                  backgroundColor: currentPage === "catalog" ? "#2563eb" : "#374151",
                  color: "#fff",
                  border: "none",
                  borderRadius: "4px",
                  padding: "6px 12px",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "bold",
                }}
              >
                Catalog
              </button>
              <button
                className="moderator-dashboard-nav-btn"
                onClick={() => setCurrentPage("moderation")}
                style={{
                  backgroundColor: currentPage === "moderation" ? "#2563eb" : "#374151",
                  color: "#fff",
                  border: "none",
                  borderRadius: "4px",
                  padding: "6px 12px",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "bold",
                }}
              >
                Moderation Dashboard
              </button>
            </nav>
          )}

          <div className="header-meta">
            <AuthStatus />
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="app-main">
        {/* Authentication Guidance overlay */}
        {authView !== "none" && (
          <div className="auth-overlay-card" style={{ maxWidth: "450px", margin: "30px auto", padding: "20px", border: "1px solid #e5e7eb", borderRadius: "8px", backgroundColor: "#f9fafb" }}>
            <div className="auth-tab-buttons" style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
              <button
                className={`tab-btn ${authView === "signin" ? "active" : ""}`}
                onClick={() => setAuthView("signin")}
                style={{
                  flex: 1,
                  padding: "10px",
                  backgroundColor: authView === "signin" ? "#2563eb" : "#e5e7eb",
                  color: authView === "signin" ? "#fff" : "#111827",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                Sign In
              </button>
              <button
                className={`tab-btn ${authView === "register" ? "active" : ""}`}
                onClick={() => setAuthView("register")}
                style={{
                  flex: 1,
                  padding: "10px",
                  backgroundColor: authView === "register" ? "#2563eb" : "#e5e7eb",
                  color: authView === "register" ? "#fff" : "#111827",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                Register
              </button>
            </div>

            {authView === "signin" ? (
              <SignInForm onSuccess={handleAuthSuccess} />
            ) : (
              <RegisterForm onSuccess={() => setAuthView("signin")} />
            )}

            <button
              className="cancel-auth-btn"
              onClick={() => setAuthView("none")}
              style={{
                width: "100%",
                padding: "8px",
                backgroundColor: "#d1d5db",
                color: "#111827",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                marginTop: "10px",
              }}
            >
              Cancel
            </button>
          </div>
        )}

        {/* Regular views rendering */}
        {authView === "none" && (
          currentPage === "catalog" ? (
            <CatalogPage onProceedToCheckout={handleProceedToCheckout} />
          ) : currentPage === "checkout" ? (
            <CheckoutPage onBackToCatalog={() => setCurrentPage("catalog")} />
          ) : (
            <ModeratorDashboard />
          )
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer-info">
        <p>Stage 2 E-Commerce Academic Demonstration. Built with React, TypeScript, Python, and FastAPI.</p>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <AuthProvider>
        <CartProvider>
          <AppContent />
        </CartProvider>
      </AuthProvider>
    </ToastProvider>
  );
};
export default App;
