import { createContext, useState, useEffect, useContext, ReactNode } from 'react';

export interface Product {
  id: number;
  name: string;
  image_url: string;
  description: string;
  price: number;
  availability: boolean;
}

export interface CartItem {
  product: Product;
  quantity: number;
}

export interface User {
  username: string;
  token: string;
}

export interface Feedback {
  type: 'success' | 'error';
  text: string;
}

export type ViewState = 'catalog' | 'cart' | 'auth' | 'checkout' | 'confirmation';

export interface CheckoutSummary {
  items: Array<{
    product_id: number;
    name: string;
    price: number;
    quantity: number;
    item_total: number;
  }>;
  total_amount: number;
  buyer: string;
}

interface AppContextType {
  view: ViewState;
  setView: (view: ViewState) => void;
  products: Product[];
  cart: CartItem[];
  user: User | null;
  loading: boolean;
  feedback: Feedback | null;
  setFeedback: (feedback: Feedback | null) => void;
  checkoutSummary: CheckoutSummary | null;
  addToCart: (product: Product) => void;
  updateQuantity: (productId: number, quantity: number) => void;
  removeFromCart: (productId: number) => void;
  clearCart: () => void;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkout: () => Promise<boolean>;
  checkoutRedirectIntent: boolean;
  setCheckoutRedirectIntent: (intent: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [view, setViewState] = useState<ViewState>('catalog');
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [feedback, setFeedbackState] = useState<Feedback | null>(null);
  const [checkoutSummary, setCheckoutSummary] = useState<CheckoutSummary | null>(null);
  const [checkoutRedirectIntent, setCheckoutRedirectIntent] = useState<boolean>(false);

  // Wrapper for showing feedback that auto-clears after 4 seconds
  const setFeedback = (msg: Feedback | null) => {
    setFeedbackState(msg);
  };

  // Fetch catalog on mount
  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/products`);
        if (!res.ok) {
          throw new Error('Failed to load products from catalog.');
        }
        const data = await res.json();
        setProducts(data);
      } catch (err: any) {
        setFeedback({ type: 'error', text: err.message || 'Network error loading catalog.' });
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, []);

  // Set the active view with clean checks
  const setView = (newView: ViewState) => {
    // If navigating to checkout but cart is empty, prevent transition
    if (newView === 'checkout' && cart.length === 0) {
      setFeedback({ type: 'error', text: 'Your shopping cart is empty. Cannot proceed to checkout.' });
      return;
    }

    // Checkout Authentication Guard
    if (newView === 'checkout' && !user) {
      setCheckoutRedirectIntent(true);
      setViewState('auth');
      setFeedback({ type: 'error', text: 'Please sign in or register to complete your checkout.' });
      return;
    }

    setViewState(newView);
  };

  // Local Shopping Cart Operations
  const addToCart = (product: Product) => {
    if (!product.availability) {
      setFeedback({ type: 'error', text: `"${product.name}" is currently out of stock.` });
      return;
    }

    setCart((prev) => {
      const existing = prev.find((item) => item.product.id === product.id);
      if (existing) {
        setFeedback({ type: 'success', text: `Increased quantity of "${product.name}" in your cart.` });
        return prev.map((item) =>
          item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      setFeedback({ type: 'success', text: `Added "${product.name}" to your cart.` });
      return [...prev, { product, quantity: 1 }];
    });
  };

  const updateQuantity = (productId: number, quantity: number) => {
    if (quantity < 1) return;
    setCart((prev) =>
      prev.map((item) =>
        item.product.id === productId ? { ...item, quantity } : item
      )
    );
    setFeedback({ type: 'success', text: 'Cart quantities updated.' });
  };

  const removeFromCart = (productId: number) => {
    const item = cart.find((i) => i.product.id === productId);
    if (!item) return;

    setCart((prev) => prev.filter((i) => i.product.id !== productId));
    setFeedback({ type: 'success', text: `Removed "${item.product.name}" from your cart.` });
  };

  const clearCart = () => {
    setCart([]);
  };

  // Authentication Operations
  const login = async (username: string, password: string): Promise<boolean> => {
    setLoading(true);
    setFeedback(null);
    try {
      const res = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to authenticate.');
      }

      setUser({ username: data.username, token: data.token });
      setFeedback({ type: 'success', text: `Welcome back, ${data.username}! Successful sign-in.` });

      // If they were trying to checkout, resume that flow immediately
      if (checkoutRedirectIntent) {
        setCheckoutRedirectIntent(false);
        setViewState('checkout');
      } else {
        setViewState('catalog');
      }
      return true;
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Login failed.' });
      return false;
    } finally {
      setLoading(false);
    }
  };

  const register = async (username: string, password: string): Promise<boolean> => {
    setLoading(true);
    setFeedback(null);
    try {
      const res = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Registration failed.');
      }

      // Successful registration automatically signs the user in and returns session
      setUser({ username: data.username, token: data.token });
      setFeedback({ type: 'success', text: `Registration successful! Welcome, ${data.username}.` });

      // If they were trying to checkout, resume that flow immediately
      if (checkoutRedirectIntent) {
        setCheckoutRedirectIntent(false);
        setViewState('checkout');
      } else {
        setViewState('catalog');
      }
      return true;
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Registration failed.' });
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    if (!user) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE_URL}/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.token}`,
        },
      });
    } catch (err) {
      // Best-effort logout; clear local state regardless of server connectivity
    } finally {
      setUser(null);
      setCheckoutRedirectIntent(false);
      setViewState('catalog');
      setFeedback({ type: 'success', text: 'You have been signed out successfully.' });
      setLoading(false);
    }
  };

  // Simulated Checkout
  const checkout = async (): Promise<boolean> => {
    if (!user) {
      setFeedback({ type: 'error', text: 'Authentication is required to perform checkout.' });
      return false;
    }
    if (cart.length === 0) {
      setFeedback({ type: 'error', text: 'Cannot checkout with an empty shopping cart.' });
      return false;
    }

    setLoading(true);
    setFeedback(null);

    try {
      const itemsPayload = cart.map((item) => ({
        product_id: item.product.id,
        quantity: item.quantity,
      }));

      const res = await fetch(`${API_BASE_URL}/checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`,
        },
        body: JSON.stringify({ items: itemsPayload }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Fictitious checkout failed.');
      }

      setCheckoutSummary(data.summary);
      setViewState('confirmation');
      setFeedback({
        type: 'success',
        text: 'Fictitious checkout completed successfully!'
      });
      return true;
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Simulated checkout failed.' });
      return false;
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppContext.Provider
      value={{
        view,
        setView,
        products,
        cart,
        user,
        loading,
        feedback,
        setFeedback,
        checkoutSummary,
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        login,
        register,
        logout,
        checkout,
        checkoutRedirectIntent,
        setCheckoutRedirectIntent,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
