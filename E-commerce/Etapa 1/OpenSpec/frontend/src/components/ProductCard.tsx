import React, { useState } from 'react';
import { useCart, Product } from '../context/CartContext';
import { ShoppingCart, Check } from 'lucide-react';

interface ProductCardProps {
  product: Product;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const { addToCart } = useCart();
  const [addedFeedback, setAddedFeedback] = useState(false);

  const handleAddToCart = () => {
    if (!product.is_available) return;
    addToCart(product);
    setAddedFeedback(true);
    setTimeout(() => {
      setAddedFeedback(false);
    }, 1500);
  };

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100 hover:shadow-lg transition-shadow flex flex-col h-full">
      {/* Product Image */}
      <div className="relative h-48 bg-gray-100 overflow-hidden flex items-center justify-center">
        <img
          src={product.image_url}
          alt={product.name}
          className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-300"
        />
        {!product.is_available && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center">
            <span className="text-white font-bold tracking-wide uppercase px-3 py-1 bg-red-600 rounded-md text-sm">
              Out of Stock
            </span>
          </div>
        )}
      </div>

      {/* Product Body */}
      <div className="p-5 flex-col flex flex-1 justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-900 tracking-tight mb-1">
            {product.name}
          </h2>
          <p className="text-indigo-600 font-bold text-xl mb-3">
            ${product.price.toFixed(2)}
          </p>
          <p className="text-gray-500 text-sm leading-relaxed mb-4">
            {product.description}
          </p>
        </div>

        {/* Action Button */}
        <div>
          <button
            onClick={handleAddToCart}
            disabled={!product.is_available}
            className={`w-full flex items-center justify-center gap-2 py-2 px-4 rounded-md font-semibold text-sm transition-all shadow-sm ${
              !product.is_available
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : addedFeedback
                ? 'bg-green-600 text-white cursor-default'
                : 'bg-indigo-600 text-white hover:bg-indigo-700 active:scale-98 cursor-pointer'
            }`}
            aria-label={
              !product.is_available
                ? `${product.name} is currently out of stock`
                : addedFeedback
                ? `${product.name} has been added to your cart`
                : `Add ${product.name} to shopping cart`
            }
          >
            {addedFeedback ? (
              <>
                <Check className="h-4 w-4 animate-bounce" />
                <span>Added!</span>
              </>
            ) : (
              <>
                <ShoppingCart className="h-4 w-4" />
                <span>Add to Cart</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
