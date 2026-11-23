import React from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { CreditCard, ArrowLeft, ArrowRight } from 'lucide-react';

export const CheckoutPage: React.FC = () => {
  const { cartItems, cartTotal } = useCart();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  // If cart is empty, block entry and redirect to cart
  if (cartItems.length === 0) {
    return <Navigate to="/cart" replace />;
  }

  // Guided Authentication Guard: If guest user is unauthenticated, guide them to log in / register
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ fromCheckout: true }} replace />;
  }

  const handleConfirmPurchase = (e: React.FormEvent) => {
    e.preventDefault();
    // Go to simulated confirmation page
    navigate('/confirmation');
  };

  return (
    <main className="max-w-2xl mx-auto px-4 py-8 flex-1 w-full">
      <div className="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden">
        {/* Header */}
        <div className="bg-indigo-600 px-6 py-4 text-white">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            <span>Simulated Checkout Summary</span>
          </h1>
          <p className="text-indigo-100 text-xs mt-1">
            Review your academic purchase order before final confirmation.
          </p>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Order Summary */}
          <h2 className="text-base font-bold text-gray-900 mb-3">Order Details</h2>
          <div className="divide-y divide-gray-150 border border-gray-150 rounded-lg p-4 bg-gray-50 mb-6 max-h-60 overflow-y-auto">
            {cartItems.map((item) => (
              <div key={item.product.id} className="py-2.5 flex justify-between items-center text-sm">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-gray-800 truncate">{item.product.name}</p>
                  <p className="text-gray-500 text-xs">
                    Qty: {item.quantity} &times; ${item.product.price.toFixed(2)}
                  </p>
                </div>
                <span className="font-bold text-gray-900 ml-4 shrink-0">
                  ${(item.product.price * item.quantity).toFixed(2)}
                </span>
              </div>
            ))}
            <div className="pt-3 flex justify-between items-center text-base font-bold text-indigo-600">
              <span>Order Total</span>
              <span>${cartTotal.toFixed(2)}</span>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleConfirmPurchase} noValidate aria-label="Simulated purchase confirmation form">
            {/* Minimal Demonstration Info Field */}
            <div className="mb-6 bg-indigo-50 border border-indigo-200 rounded-lg p-4">
              <p className="text-sm text-indigo-900 font-medium leading-relaxed">
                This is a simulated purchase for demonstration purposes. No real transaction will be made, and no real payment data is requested.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 items-center justify-between border-t border-gray-100 pt-6">
              <button
                type="button"
                onClick={() => navigate('/cart')}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 text-gray-600 font-semibold py-2.5 px-4 rounded-md hover:bg-gray-50 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Return to Cart</span>
              </button>

              <button
                type="submit"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-indigo-600 text-white font-bold py-2.5 px-6 rounded-md hover:bg-indigo-700 transition-colors shadow-xs cursor-pointer"
                aria-label="Confirm Purchase (Simulation)"
              >
                <span>Confirm Purchase</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </main>
  );
};
