import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import { Header } from './components/Header';
import { CatalogPage } from './pages/CatalogPage';
import { CartPage } from './pages/CartPage';
import { LoginPage } from './pages/LoginPage';
import { CheckoutPage } from './pages/CheckoutPage';
import { ConfirmationPage } from './pages/ConfirmationPage';

const App: React.FC = () => {
  return (
    <AuthProvider>
      <CartProvider>
        <BrowserRouter>
          <div className="min-h-screen flex flex-col bg-gray-50 text-gray-900 selection:bg-indigo-500 selection:text-white">
            {/* Responsive Navigation Header */}
            <Header />

            {/* Main Layout Area */}
            <div className="flex-1 flex flex-col">
              <Routes>
                {/* Catalog Landing Route */}
                <Route path="/" element={<CatalogPage />} />

                {/* Shopping Cart Route */}
                <Route path="/cart" element={<CartPage />} />

                {/* Secure Authentication Form Routes (Registration & login toggled inside) */}
                <Route path="/login" element={<LoginPage />} />

                {/* Simulated Checkout Guarded Summary Route */}
                <Route path="/checkout" element={<CheckoutPage />} />

                {/* Fictitious Checkout Confirmation Receipt Route */}
                <Route path="/confirmation" element={<ConfirmationPage />} />

                {/* Catch-all Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>

            {/* Academic Footer */}
            <footer className="bg-white border-t border-gray-150 py-6 text-center text-xs text-gray-400 font-medium">
              <div className="max-w-6xl mx-auto px-4">
                <p>&copy; 2026 Academic Store. Designed and implemented strictly in English for academic demonstration purposes only.</p>
              </div>
            </footer>
          </div>
        </BrowserRouter>
      </CartProvider>
    </AuthProvider>
  );
};

export default App;
