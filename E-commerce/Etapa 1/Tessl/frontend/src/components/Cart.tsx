import { useApp } from '../context/AppContext';

export default function Cart() {
  const { cart, updateQuantity, removeFromCart, setView } = useApp();

  const totalAmount = cart.reduce((sum, item) => sum + item.product.price * item.quantity, 0);

  if (cart.length === 0) {
    return (
      <div className="cart-card">
        <div className="cart-empty">
          <div className="cart-empty-icon" aria-hidden="true">🛒</div>
          <h2>Your Shopping Cart is Empty</h2>
          <p>Please browse the catalog and add some products before checking out.</p>
          <button
            className="nav-btn primary"
            style={{ marginTop: '1.5rem' }}
            onClick={() => setView('catalog')}
          >
            Go to Catalog
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="cart-card" aria-label="Shopping Cart">
      <h1 className="catalog-title">Your Shopping Cart</h1>

      <div className="cart-items-list">
        {cart.map((item) => (
          <div key={item.product.id} className="cart-item">
            <div className="cart-item-info">
              <div className="cart-item-image-container">
                <img
                  src={item.product.image_url}
                  alt={item.product.name}
                  className="cart-item-image"
                />
              </div>
              <div className="cart-item-meta">
                <h3>{item.product.name}</h3>
                <p>Price: ${item.product.price.toFixed(2)}</p>
              </div>
            </div>

            <div className="cart-item-controls">
              <label htmlFor={`qty-${item.product.id}`} className="hidden-label">
                Quantity for {item.product.name}
              </label>
              <button
                className="quantity-btn"
                onClick={() => updateQuantity(item.product.id, item.quantity - 1)}
                disabled={item.quantity <= 1}
                aria-label={`Decrease quantity of ${item.product.name}`}
              >
                -
              </button>
              <span id={`qty-${item.product.id}`} className="quantity-value" aria-live="polite">
                {item.quantity}
              </span>
              <button
                className="quantity-btn"
                onClick={() => updateQuantity(item.product.id, item.quantity + 1)}
                aria-label={`Increase quantity of ${item.product.name}`}
              >
                +
              </button>
            </div>

            <div style={{ fontWeight: '600', minWidth: '80px', textAlign: 'right' }}>
              ${(item.product.price * item.quantity).toFixed(2)}
            </div>

            <div>
              <button
                className="remove-btn"
                onClick={() => removeFromCart(item.product.id)}
                aria-label={`Remove ${item.product.name} from cart`}
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="cart-totals">
        <span className="cart-total-label">Total:</span>
        <span className="cart-total-value">${totalAmount.toFixed(2)}</span>
      </div>

      <div className="cart-actions">
        <button className="nav-btn" onClick={() => setView('catalog')}>
          Continue Shopping
        </button>
        <button
          className="nav-btn primary"
          onClick={() => setView('checkout')}
          aria-label="Proceed to checkout summary"
        >
          Proceed to Checkout
        </button>
      </div>
    </div>
  );
}
