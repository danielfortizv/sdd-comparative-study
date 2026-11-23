import { useApp } from '../context/AppContext';

export default function Checkout() {
  const { view, setView, cart, checkout, checkoutSummary, clearCart, loading } = useApp();

  const cartTotalAmount = cart.reduce((sum, item) => sum + item.product.price * item.quantity, 0);

  // View 1: Checkout Summary and Simulated Process
  if (view === 'checkout') {
    return (
      <div className="checkout-grid">
        <div className="checkout-card">
          <h1 className="catalog-title">Simulated Checkout</h1>
          
          <div className="fictitious-warning" role="alert">
            <strong>⚠️ Fictitious Journey Notice:</strong> This is a simulated checkout journey. 
            No real payment or financial charge is executed, and no external payment gateway is contacted.
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <h2 className="checkout-subtitle">Purchase Contents</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {cart.map((item) => (
                <div key={item.product.id} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                  <div>
                    <span style={{ fontWeight: '600' }}>{item.product.name}</span>
                    <span style={{ color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>x{item.quantity}</span>
                  </div>
                  <span>${(item.product.price * item.quantity).toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="checkout-card" style={{ height: 'fit-content' }}>
          <h2 className="checkout-subtitle">Order Summary</h2>
          <div className="checkout-summary-list">
            <div className="checkout-summary-item">
              <span>Subtotal</span>
              <span>${cartTotalAmount.toFixed(2)}</span>
            </div>
            <div className="checkout-summary-item">
              <span>Simulated Shipping</span>
              <span style={{ color: 'var(--success-color)' }}>FREE (Simulated)</span>
            </div>
            <div className="checkout-summary-item checkout-summary-total">
              <span>Total Amount</span>
              <span>${cartTotalAmount.toFixed(2)}</span>
            </div>
          </div>

          <button
            className="auth-submit-btn"
            style={{ width: '100%', margin: '0' }}
            onClick={checkout}
            disabled={loading}
          >
            {loading ? 'Processing Simulated Order...' : 'Confirm Simulated Purchase'}
          </button>
          
          <button
            className="nav-btn"
            style={{ width: '100%', marginTop: '0.75rem' }}
            onClick={() => setView('cart')}
            disabled={loading}
          >
            Back to Cart
          </button>
        </div>
      </div>
    );
  }

  // View 2: Fictitious Confirmation and Purchase Summary
  if (view === 'confirmation' && checkoutSummary) {
    const handleStartNewPurchase = () => {
      // Clear the local cart state
      clearCart();
      // Reset view back to catalog
      setView('catalog');
    };

    return (
      <div className="confirmation-container">
        <div className="success-badge" aria-hidden="true">✔</div>
        <h1 className="confirmation-title">Simulated Purchase Confirmed!</h1>
        <p className="confirmation-msg">
          Your simulated checkout completed successfully. 
          As a reminder, this was a demonstration. No real charge has been made.
        </p>

        <div className="confirmation-summary">
          <h2 className="checkout-subtitle" style={{ fontSize: '1.1rem', marginBottom: '0.75rem' }}>
            Simulated Purchase Summary
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Buyer: <strong>{checkoutSummary.buyer}</strong>
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
            {checkoutSummary.items.map((item) => (
              <div key={item.product_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
                <span>{item.name} (x{item.quantity})</span>
                <span>${item.item_total.toFixed(2)}</span>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '2px solid var(--border-color)', paddingTop: '0.5rem', fontWeight: '700' }}>
            <span>Total Simulated Charge</span>
            <span>${checkoutSummary.total_amount.toFixed(2)}</span>
          </div>
        </div>

        <button
          className="auth-submit-btn"
          style={{ padding: '0.75rem 1.5rem', margin: '0 auto' }}
          onClick={handleStartNewPurchase}
        >
          Start New Purchase
        </button>
      </div>
    );
  }

  return null;
}
