import React, { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CartProvider, useCart, CartItem } from './context/CartContext';

const API_BASE = 'http://127.0.0.1:8000';

interface Product {
  id: number;
  name: string;
  price: number;
  description: string;
  availability: string;
  image_svg: string;
}

interface OrderSummary {
  items: Array<{
    id: number;
    name: string;
    quantity: number;
    price: number;
    subtotal: number;
  }>;
  total: number;
}

const AppContent: React.FC = () => {
  const { user, isAuthenticated, login, logout } = useAuth();
  const {
    cartItems,
    addToCart,
    updateQuantity,
    removeFromCart,
    clearCart,
    cartTotal,
    cartCount,
    cartFeedback,
    triggerFeedback,
  } = useCart();

  // Navigation state: 'catalog' | 'cart' | 'auth' | 'checkout' | 'confirmation'
  const [activeView, setActiveView] = useState<'catalog' | 'cart' | 'auth' | 'checkout' | 'confirmation'>('catalog');
  
  // API loading states
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoadingProducts, setIsLoadingProducts] = useState<boolean>(true);
  const [productsError, setProductsError] = useState<string | null>(null);

  // Authentication form states
  const [authTab, setAuthTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [isSubmittingAuth, setIsSubmittingAuth] = useState<boolean>(false);

  // Checkout submission states
  const [isSubmittingCheckout, setIsSubmittingCheckout] = useState<boolean>(false);
  const [confirmationSummary, setConfirmationSummary] = useState<OrderSummary | null>(null);

  // Fetch products catalog on mount
  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    setIsLoadingProducts(true);
    setProductsError(null);
    try {
      const res = await fetch(`${API_BASE}/api/products`);
      if (!res.ok) {
        throw new Error('Failed to retrieve catalog products from the server.');
      }
      const data = await res.json();
      setProducts(data);
    } catch (err: any) {
      setProductsError(err.message || 'Error communicating with backend API.');
    } finally {
      setIsLoadingProducts(false);
    }
  };

  // Auth actions
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);

    const trimmedUsername = username.trim();
    if (!trimmedUsername || !password) {
      setAuthError('All fields are required. Please fill in both username and password.');
      return;
    }

    setIsSubmittingAuth(true);
    const endpoint = authTab === 'register' ? '/api/register' : '/api/login';

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: trimmedUsername, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed.');
      }

      if (authTab === 'register') {
        // Automatically switch to login tab and notify success
        setAuthTab('login');
        setPassword('');
        triggerFeedback('Registration successful! Please sign in using your new credentials.');
      } else {
        // Log in user
        login(data.username);
        triggerFeedback('Welcome back! You have successfully signed in.');
        // Return to the local cart view so they can proceed in their journey
        setActiveView('cart');
        // Clean credentials fields
        setUsername('');
        setPassword('');
      }
    } catch (err: any) {
      setAuthError(err.message || 'Error connecting to the authentication server.');
    } finally {
      setIsSubmittingAuth(false);
    }
  };

  // Proceed from Cart View to Checkout View
  const handleProceedToCheckout = () => {
    if (cartItems.length === 0) {
      triggerFeedback('Your cart is empty. Add products before proceeding.');
      return;
    }

    if (!isAuthenticated) {
      triggerFeedback('Identification required. Please register or sign in to continue.');
      setActiveView('auth');
    } else {
      setActiveView('checkout');
    }
  };

  // Submit simulated order
  const handleConfirmPurchase = async () => {
    if (cartItems.length === 0) {
      triggerFeedback('Cannot submit. Your cart is empty.');
      return;
    }

    setIsSubmittingCheckout(true);
    try {
      const res = await fetch(`${API_BASE}/api/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: cartItems.map(item => ({
            id: item.id,
            quantity: item.quantity,
            price: item.price,
          })),
          summary_total: cartTotal,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to submit purchase.');
      }

      // Store confirmation order summary details
      setConfirmationSummary(data.order_summary);
      triggerFeedback('Simulated purchase completed successfully!');
      setActiveView('confirmation');
    } catch (err: any) {
      triggerFeedback(err.message || 'Checkout failed.');
    } finally {
      setIsSubmittingCheckout(false);
    }
  };

  // Start new purchase journey (comprehensible reset state)
  const handleResetPurchase = () => {
    clearCart();
    setConfirmationSummary(null);
    setActiveView('catalog');
  };

  return (
    <div className="container">
      {/* Alert Portal for Immediate Feedback */}
      {cartFeedback && (
        <div className="alert-container">
          <div className="alert">{cartFeedback}</div>
        </div>
      )}

      {/* Header and Authentication Indicators */}
      <header className="navbar">
        <div className="navbar-brand" onClick={() => setActiveView('catalog')}>
          🛒 Demo E-Commerce
        </div>
        
        <div className="navbar-session">
          <div className="user-status">
            {isAuthenticated ? (
              <span>
                Session: <span className="user-status-active">Active</span> ({user})
              </span>
            ) : (
              <span>No active session (Guest)</span>
            )}
          </div>
          {isAuthenticated && (
            <button className="btn btn-outline" onClick={() => { logout(); triggerFeedback('Signed out.'); setActiveView('catalog'); }}>
              Sign Out
            </button>
          )}
        </div>

        {/* Global tab navigation */}
        <nav className="nav-tabs">
          <button 
            className={`btn btn-tab ${activeView === 'catalog' ? 'active' : ''}`}
            onClick={() => setActiveView('catalog')}
          >
            Products
          </button>
          <button 
            className={`btn btn-tab ${activeView === 'cart' ? 'active' : ''}`}
            onClick={() => setActiveView('cart')}
          >
            Cart ({cartCount})
          </button>
          {!isAuthenticated && activeView !== 'confirmation' && (
            <button 
              className={`btn btn-tab ${activeView === 'auth' ? 'active' : ''}`}
              onClick={() => { setAuthError(null); setActiveView('auth'); }}
            >
              Sign In
            </button>
          )}
        </nav>
      </header>

      {/* Main View Swapping Layout */}
      <main>
        {/* VIEW 1: CATALOG */}
        {activeView === 'catalog' && (
          <div>
            <h2 style={{ marginBottom: '1.5rem' }}>Product Catalog</h2>
            {isLoadingProducts ? (
              <p style={{ textAlign: 'center', padding: '3rem 0' }}>Loading available products...</p>
            ) : productsError ? (
              <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                <p className="form-error" style={{ marginBottom: '1rem' }}>{productsError}</p>
                <button className="btn btn-primary" onClick={fetchProducts}>Retry Connection</button>
              </div>
            ) : (
              <div className="catalog-grid">
                {products.map((product) => (
                  <div key={product.id} className="product-card">
                    <div>
                      <div className="product-image-container" dangerouslySetInnerHTML={{ __html: product.image_svg }} />
                      <h3 className="product-name">{product.name}</h3>
                      <p className="product-description">{product.description}</p>
                    </div>
                    <div>
                      <div className="product-meta">
                        <span className="product-price">${product.price.toFixed(2)}</span>
                        <span className={`product-availability ${product.availability === 'In Stock' ? 'availability-in-stock' : 'availability-out-of-stock'}`}>
                          {product.availability}
                        </span>
                      </div>
                      <button
                        className="btn btn-primary"
                        style={{ width: '100%' }}
                        disabled={product.availability !== 'In Stock'}
                        onClick={() => addToCart(product)}
                      >
                        Add to Cart
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: SHOPPING CART */}
        {activeView === 'cart' && (
          <div className="cart-view">
            <h2 style={{ marginBottom: '1.5rem' }}>Shopping Cart</h2>
            
            {cartItems.length === 0 ? (
              <div className="cart-empty">
                <p style={{ fontSize: '1.15rem', marginBottom: '1.5rem' }}>Your shopping cart is currently empty.</p>
                <button className="btn btn-primary" onClick={() => setActiveView('catalog')}>Browse Products</button>
              </div>
            ) : (
              <div>
                <div className="cart-items-list">
                  {cartItems.map((item) => (
                    <div key={item.id} className="cart-item">
                      <div className="cart-item-info">
                        <div className="cart-item-svg" dangerouslySetInnerHTML={{ __html: item.image_svg }} />
                        <div className="cart-item-details">
                          <h4>{item.name}</h4>
                          <p>Price: ${item.price.toFixed(2)}</p>
                        </div>
                      </div>
                      
                      <div className="cart-item-controls">
                        <button className="quantity-btn" onClick={() => updateQuantity(item.id, item.quantity - 1)}>-</button>
                        <span className="item-quantity">{item.quantity}</span>
                        <button className="quantity-btn" onClick={() => updateQuantity(item.id, item.quantity + 1)}>+</button>
                        
                        <span className="cart-item-subtotal">${(item.price * item.quantity).toFixed(2)}</span>
                        
                        <button className="btn btn-danger" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }} onClick={() => removeFromCart(item.id)}>
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="cart-summary-section">
                  <div className="cart-total-display">
                    Total: <span className="cart-total-amount">${cartTotal.toFixed(2)}</span>
                  </div>
                  <button className="btn btn-primary" onClick={handleProceedToCheckout}>
                    Proceed to Checkout
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* VIEW 3: AUTHENTICATION (Login / Registration) */}
        {activeView === 'auth' && (
          <div className="auth-panel">
            <div className="auth-tabs">
              <button 
                className={`auth-tab-btn ${authTab === 'login' ? 'active' : ''}`}
                onClick={() => { setAuthTab('login'); setAuthError(null); }}
              >
                Sign In
              </button>
              <button 
                className={`auth-tab-btn ${authTab === 'register' ? 'active' : ''}`}
                onClick={() => { setAuthTab('register'); setAuthError(null); }}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleAuthSubmit}>
              {authError && <div className="form-general-error">{authError}</div>}
              
              <div className="form-group">
                <label className="form-label" htmlFor="username">Username / Identifier</label>
                <input 
                  className="form-input"
                  type="text" 
                  id="username"
                  placeholder="e.g. customer123"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                <span className="form-explanation">
                  Please enter your minimum identifying customer username.
                </span>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="password">Password</label>
                <input 
                  className="form-input"
                  type="password" 
                  id="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <span className="form-explanation">
                  Please enter your authentication password.
                </span>
              </div>

              <button 
                type="submit" 
                className="btn btn-primary" 
                style={{ width: '100%', marginTop: '1rem' }}
                disabled={isSubmittingAuth}
              >
                {isSubmittingAuth ? 'Processing...' : authTab === 'register' ? 'Create Account' : 'Sign In'}
              </button>
            </form>
          </div>
        )}

        {/* VIEW 4: SIMULATED CHECKOUT */}
        {activeView === 'checkout' && (
          <div className="checkout-view">
            <h2>Review Order Summary</h2>
            
            <div className="fictitious-warning">
              ⚠️ <strong>Fictitious Checkout Notice:</strong> This is a simulated transaction. No actual monetary charges are made, and no real payment gateway is contacted.
            </div>

            <div className="checkout-summary-box">
              <div className="checkout-summary-title">Summary of Items</div>
              {cartItems.map(item => (
                <div key={item.id} className="checkout-summary-item">
                  <span>{item.name} (x{item.quantity})</span>
                  <span>${(item.price * item.quantity).toFixed(2)}</span>
                </div>
              ))}
              <div className="checkout-summary-total">
                <span>Grand Total:</span>
                <span>${cartTotal.toFixed(2)}</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-outline" onClick={() => setActiveView('cart')}>
                Back to Cart
              </button>
              <button 
                className="btn btn-primary" 
                disabled={isSubmittingCheckout || cartItems.length === 0}
                onClick={handleConfirmPurchase}
              >
                {isSubmittingCheckout ? 'Confirming...' : 'Confirm Simulated Purchase'}
              </button>
            </div>
          </div>
        )}

        {/* VIEW 5: PURCHASE CONFIRMATION */}
        {activeView === 'confirmation' && confirmationSummary && (
          <div className="confirmation-view">
            <svg className="confirmation-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            
            <h2 className="confirmation-title">Thank You For Your Simulated Order!</h2>
            <p className="confirmation-message">Your fictitious transaction has been successfully confirmed. No charges were made.</p>

            <div className="confirmation-summary">
              <h4>Order Summary</h4>
              {confirmationSummary.items.map(item => (
                <div key={item.id} className="checkout-summary-item" style={{ fontSize: '0.85rem' }}>
                  <span>{item.name} (x{item.quantity})</span>
                  <span>${item.subtotal.toFixed(2)}</span>
                </div>
              ))}
              <div className="checkout-summary-total" style={{ fontSize: '0.95rem' }}>
                <span>Total Simulated Cost:</span>
                <span>${confirmationSummary.total.toFixed(2)}</span>
              </div>
            </div>

            <button className="btn btn-primary" onClick={handleResetPurchase}>
              Start New Purchase
            </button>
          </div>
        )}
      </main>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <CartProvider>
        <AppContent />
      </CartProvider>
    </AuthProvider>
  );
};

export default App;
