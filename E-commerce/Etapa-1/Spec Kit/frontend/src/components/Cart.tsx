import React from "react";
import { useCart } from "../context/CartContext";
import { useToast } from "./FeedbackToast";

export const Cart: React.FC<{ onProceedToCheckout?: () => void }> = ({ onProceedToCheckout }) => {
  const { items, accumulated_total, updateQuantity, removeItem } = useCart();
  const { showToast } = useToast();

  const handleQtyChange = (productId: string, name: string, quantity: number) => {
    updateQuantity(productId, quantity);
    if (quantity <= 0) {
      showToast(`Removed ${name} from your shopping cart.`, "info");
    } else {
      showToast(`Updated ${name} quantity.`, "success");
    }
  };

  const handleRemove = (productId: string, name: string) => {
    removeItem(productId);
    showToast(`Removed ${name} from your local shopping cart.`, "info");
  };

  if (items.length === 0) {
    return (
      <div className="cart-empty-container" data-testid="empty-cart-state">
        <h2 className="section-title">Local Shopping Cart</h2>
        <p className="empty-message">Your shopping cart is currently empty. Explore the catalog offering to select products.</p>
      </div>
    );
  }

  return (
    <div className="cart-container" data-testid="cart">
      <h2 className="section-title">Local Shopping Cart</h2>
      <div className="cart-item-list">
        {items.map((item) => (
          <div key={item.product_id} className="cart-item" data-testid="cart-item">
            <div className="cart-item-info">
              <h3 className="cart-item-name">{item.name}</h3>
              <p className="cart-item-price">${item.unit_price.toFixed(2)} each</p>
            </div>
            <div className="cart-item-actions">
              <div className="qty-controls">
                <button
                  className="qty-btn"
                  onClick={() => handleQtyChange(item.product_id, item.name, item.quantity - 1)}
                  aria-label={`Decrease quantity of ${item.name}`}
                >
                  -
                </button>
                <input
                  type="number"
                  className="qty-input"
                  value={item.quantity}
                  onChange={(e) => handleQtyChange(item.product_id, item.name, parseInt(e.target.value) || 0)}
                  aria-label={`Quantity of ${item.name}`}
                />
                <button
                  className="qty-btn"
                  onClick={() => handleQtyChange(item.product_id, item.name, item.quantity + 1)}
                  aria-label={`Increase quantity of ${item.name}`}
                >
                  +
                </button>
              </div>
              <span className="cart-item-subtotal">${item.subtotal.toFixed(2)}</span>
              <button
                className="remove-item-btn"
                onClick={() => handleRemove(item.product_id, item.name)}
                aria-label={`Remove ${item.name} from cart`}
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="cart-summary">
        <div className="cart-total-row">
          <span className="total-label">Accumulated Total:</span>
          <span className="total-price" data-testid="cart-total">${accumulated_total.toFixed(2)}</span>
        </div>
        {onProceedToCheckout && (
          <button
            className="checkout-proceed-btn"
            onClick={onProceedToCheckout}
            aria-label="Proceed to Checkout"
          >
            Proceed to Checkout
          </button>
        )}
      </div>
    </div>
  );
};
export default Cart;
