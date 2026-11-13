import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { Plus, Minus, Trash2, ArrowRight, ArrowLeft, ShoppingCart, Info } from 'lucide-react';

export const CartPage: React.FC = () => {
  const { cartItems, cartTotal, updateQuantity, removeFromCart } = useCart();
  const navigate = useNavigate();

  const handleCheckoutRedirect = () => {
    if (cartItems.length === 0) return;
    navigate('/checkout');
  };

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
      <div className="mb-8 flex items-center gap-2">
        <ShoppingCart className="h-8 w-8 text-indigo-600" />
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
          Shopping Cart
        </h1>
      </div>

      {cartItems.length === 0 ? (
        /* Empty Cart State */
        <div className="text-center py-16 bg-white rounded-xl shadow-xs border border-gray-150 p-8 max-w-md mx-auto">
          <Info className="h-12 w-12 text-indigo-500 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-gray-900 mb-1">Your cart is empty</h2>
          <p className="text-gray-500 text-sm mb-6">
            Add items from our catalog to begin your shopping journey.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 bg-indigo-600 text-white font-semibold px-5 py-2.5 rounded-md hover:bg-indigo-700 transition-colors shadow-sm cursor-pointer"
            aria-label="Go back to product catalog"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Browse Catalog</span>
          </Link>
        </div>
      ) : (
        /* Cart List and Calculations */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Items List */}
          <div className="lg:col-span-2 space-y-4">
            {cartItems.map((item) => (
              <div
                key={item.product.id}
                className="bg-white rounded-xl p-4 border border-gray-100 shadow-xs flex gap-4 items-center"
              >
                {/* Product Thumbnail */}
                <img
                  src={item.product.image_url}
                  alt={item.product.name}
                  className="w-20 h-20 rounded-md object-cover bg-gray-50"
                />

                {/* Details & Adjusters */}
                <div className="flex-1 min-w-0">
                  <h2 className="text-base font-bold text-gray-900 truncate">
                    {item.product.name}
                  </h2>
                  <p className="text-indigo-600 font-semibold text-sm mt-0.5">
                    ${item.product.price.toFixed(2)}
                  </p>

                  {/* Quantity Controls */}
                  <div className="flex items-center gap-3 mt-3">
                    <button
                      onClick={() => updateQuantity(item.product.id, item.quantity - 1)}
                      className="p-1 border border-gray-300 rounded-md hover:bg-gray-100 text-gray-600 transition-colors cursor-pointer"
                      aria-label={`Decrease quantity of ${item.product.name}`}
                    >
                      <Minus className="h-4 w-4" />
                    </button>
                    <span
                      className="font-bold text-gray-800 text-sm w-6 text-center"
                      aria-live="polite"
                    >
                      {item.quantity}
                    </span>
                    <button
                      onClick={() => updateQuantity(item.product.id, item.quantity + 1)}
                      className="p-1 border border-gray-300 rounded-md hover:bg-gray-100 text-gray-600 transition-colors cursor-pointer"
                      aria-label={`Increase quantity of ${item.product.name}`}
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Subtotal & Delete */}
                <div className="flex flex-col items-end gap-3">
                  <span className="text-gray-900 font-bold text-base">
                    ${(item.product.price * item.quantity).toFixed(2)}
                  </span>
                  <button
                    onClick={() => removeFromCart(item.product.id)}
                    className="p-1.5 text-gray-400 hover:text-red-500 rounded-md hover:bg-red-50 transition-colors cursor-pointer"
                    aria-label={`Remove ${item.product.name} from cart`}
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Cart Summary */}
          <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-xs h-fit">
            <h2 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-3 mb-4">
              Order Summary
            </h2>
            <div className="flex justify-between items-center text-gray-600 mb-4">
              <span>Items Subtotal</span>
              <span className="font-semibold text-gray-900">
                ${cartTotal.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between items-center text-lg font-bold text-gray-900 border-t border-gray-100 pt-4 mb-6">
              <span>Cumulative Total</span>
              <span className="text-indigo-600">${cartTotal.toFixed(2)}</span>
            </div>

            <button
              onClick={handleCheckoutRedirect}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white font-bold py-3 px-4 rounded-md hover:bg-indigo-700 transition-colors shadow-xs cursor-pointer"
              aria-label="Proceed to Simulated Checkout"
            >
              <span>Proceed to Checkout</span>
              <ArrowRight className="h-4 w-4" />
            </button>
            <Link
              to="/"
              className="mt-4 w-full flex items-center justify-center gap-2 border border-gray-300 text-gray-600 font-semibold py-2.5 px-4 rounded-md hover:bg-gray-50 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Continue Shopping</span>
            </Link>
          </div>
        </div>
      )}
    </main>
  );
};
