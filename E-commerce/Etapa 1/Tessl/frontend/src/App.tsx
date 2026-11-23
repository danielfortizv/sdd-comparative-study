import { AppProvider, useApp } from './context/AppContext';
import Header from './components/Header';
import Catalog from './components/Catalog';
import Cart from './components/Cart';
import Auth from './components/Auth';
import Checkout from './components/Checkout';

function MainAppContent() {
  const { view, feedback, setFeedback } = useApp();

  return (
    <div className="app-container">
      <Header />
      <main>
        {feedback && (
          <div className={`feedback-banner ${feedback.type}`} role="status" aria-live="polite">
            <span>{feedback.text}</span>
            <button 
              className="feedback-close" 
              onClick={() => setFeedback(null)} 
              aria-label="Close feedback message"
            >
              &times;
            </button>
          </div>
        )}

        {view === 'catalog' && <Catalog />}
        {view === 'cart' && <Cart />}
        {view === 'auth' && <Auth />}
        {(view === 'checkout' || view === 'confirmation') && <Checkout />}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <MainAppContent />
    </AppProvider>
  );
}
