import { useApp } from '../context/AppContext';

export default function Header() {
  const { view, setView, user, cart, logout } = useApp();

  const cartItemCount = cart.reduce((total, item) => total + item.quantity, 0);

  return (
    <header className="header">
      <div className="navbar">
        <div className="nav-brand" onClick={() => setView('catalog')} role="button" tabIndex={0} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setView('catalog')}>
          E-Commerce Demo
        </div>

        <div className="nav-controls">
          <span className="session-status">
            {user ? `Signed in as: ${user.username}` : 'Not Signed In'}
          </span>

          <button
            className={`nav-btn ${view === 'catalog' ? 'primary' : ''}`}
            onClick={() => setView('catalog')}
          >
            Catalog
          </button>

          <button
            className={`nav-btn ${view === 'cart' ? 'primary' : ''}`}
            onClick={() => setView('cart')}
          >
            Cart
            {cartItemCount > 0 && <span className="cart-badge">{cartItemCount}</span>}
          </button>

          {user ? (
            <button className="nav-btn" onClick={logout}>
              Sign Out
            </button>
          ) : (
            <button
              className={`nav-btn ${view === 'auth' ? 'primary' : ''}`}
              onClick={() => setView('auth')}
            >
              Sign In
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
