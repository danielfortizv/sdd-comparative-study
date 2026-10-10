import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { CheckCircle2, ArrowRight, ShieldAlert, ShoppingBag } from 'lucide-react';

export const ConfirmationPage: React.FC = () => {
  const { cartItems, cartTotal, clearCart } = useCart();

  // Keep a local copy of cart details for rendering before we clear the state!
  const [summaryItems] = React.useState([...cartItems]);
  const [summaryTotal] = React.useState(cartTotal);

  // Clear the active local shopping cart immediately upon loading the confirmation screen
  useEffect(() => {
    if (cartItems.length > 0) {
      clearCart();
    }
  }, []);

  // Safeguard: If there was no purchase (empty copy), redirect to Catalog
  if (summaryItems.length === 0) {
    return <Link to="/" className="text-indigo-600 p-8 block text-center font-bold">Return to Catalog</Link>;
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-8 flex-1 w-full">
      <div className="bg-white rounded-xl shadow-md border border-gray-150 p-6 sm:p-8 text-center">
        {/* Success Icon */}
        <div className="flex justify-center mb-4">
          <CheckCircle2 className="h-16 w-16 text-green-500 animate-bounce" />
        </div>

        {/* Title & Success feedback */}
        <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight mb-2">
          Simulated Purchase Confirmed!
        </h1>
        <p className="text-gray-500 text-sm mb-6">
          Thank you for exploring this demonstration store. Your simulated order was processed successfully.
        </p>

        {/* Fictitious Gateway Warning Box */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-8 text-left flex gap-3">
          <ShieldAlert className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <h2 className="text-sm font-bold text-amber-900">Academic Demonstration Notice</h2>
            <p className="text-amber-800 text-xs mt-1 leading-relaxed">
              This is a demonstration store. <strong className="font-bold text-amber-950">No real charges have been made, and no real payment gateway was contacted.</strong> Your shopping cart has been cleared, leaving the system in a clean state to start a new purchase journey.
            </p>
          </div>
        </div>

        {/* Purchase Summary */}
        <div className="border border-gray-150 rounded-lg p-5 text-left bg-gray-50 mb-8">
          <h2 className="text-base font-bold text-gray-900 border-b border-gray-250 pb-2 mb-3">
            Simulated Receipt
          </h2>
          <div className="divide-y divide-gray-150">
            {summaryItems.map((item) => (
              <div key={item.product.id} className="py-2.5 flex justify-between items-center text-sm">
                <span className="text-gray-700 truncate max-w-xs">{item.product.name}</span>
                <span className="text-gray-900 font-semibold shrink-0 ml-4">
                  {item.quantity} &times; ${item.product.price.toFixed(2)}
                </span>
              </div>
            ))}
            <div className="pt-3 flex justify-between items-center text-base font-extrabold text-indigo-600">
              <span>Simulated Total</span>
              <span>${summaryTotal.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Start New Purchase Button */}
        <div>
          <Link
            to="/"
            className="inline-flex items-center gap-2 bg-indigo-600 text-white font-bold px-6 py-3 rounded-md hover:bg-indigo-700 transition-colors shadow-sm cursor-pointer"
            aria-label="Start a new simulated purchase journey"
          >
            <ShoppingBag className="h-4 w-4" />
            <span>Start New Purchase</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </main>
  );
};
