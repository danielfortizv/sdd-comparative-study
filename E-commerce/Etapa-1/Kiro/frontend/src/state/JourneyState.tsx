// In-memory journey state shared across views (design: Shared Journey State).
//
// The cart is the authoritative client-side list of CartItem, held in memory
// only with no durable persistence across browser closures or separate
// sessions (Requirements 4.1, 4.2, 4.3). Session state carries no password or
// credential value (Requirement 7.3).
//
// Cart operations and the derived cart view are implemented as pure functions
// in ./cart and exposed here as convenient actions so views consume a single
// source of totals (Requirements 3.1, 3.2, 11.4, 11.5).

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { CartItem, CartView, Product, SessionState } from "../types";
import {
  activeSession,
  addItem,
  adjustQuantity as adjustQuantityPure,
  clearCart as clearCartPure,
  deriveCartView,
  inactiveSession,
  removeItem,
} from "./cart";

export interface JourneyState {
  /** Authoritative, in-memory cart contents. */
  cart: CartItem[];
  /** Catalog products loaded from the backend, used to resolve cart details. */
  catalog: Product[];
  /** In-memory session representation (no credentials held). */
  session: SessionState;
  /**
   * Derived cart view (per-item unit price and line total, plus the accumulated
   * total). Single source of totals used by the Cart and Checkout views.
   */
  cartView: CartView;
  setCart: (cart: CartItem[]) => void;
  setCatalog: (catalog: Product[]) => void;
  setSession: (session: SessionState) => void;
  /** Add a product to the cart (incrementing quantity if already present). */
  addToCart: (productId: string, quantity?: number) => void;
  /** Remove a product entirely from the cart. */
  removeFromCart: (productId: string) => void;
  /** Adjust a product's quantity by a relative delta (clamped to removal). */
  adjustQuantity: (productId: string, delta: number) => void;
  /** Empty the cart (reset-to-new-purchase). */
  clearCart: () => void;
  /** Establish an active in-memory session for the given display identity. */
  signInSession: (identity: string) => void;
  /** End the active in-memory session. */
  signOutSession: () => void;
}

const INITIAL_SESSION: SessionState = { active: false, identity: null };

const JourneyContext = createContext<JourneyState | null>(null);

export function JourneyProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [catalog, setCatalog] = useState<Product[]>([]);
  const [session, setSession] = useState<SessionState>(INITIAL_SESSION);

  const addToCart = useCallback(
    (productId: string, quantity: number = 1) =>
      setCart((current) => addItem(current, productId, quantity)),
    [],
  );

  const removeFromCart = useCallback(
    (productId: string) => setCart((current) => removeItem(current, productId)),
    [],
  );

  const adjustQuantity = useCallback(
    (productId: string, delta: number) =>
      setCart((current) => adjustQuantityPure(current, productId, delta)),
    [],
  );

  const clearCart = useCallback(() => setCart(clearCartPure()), []);

  const signInSession = useCallback(
    (identity: string) => setSession(activeSession(identity)),
    [],
  );

  const signOutSession = useCallback(
    () => setSession(inactiveSession()),
    [],
  );

  const cartView = useMemo<CartView>(
    () => deriveCartView(cart, catalog),
    [cart, catalog],
  );

  const value = useMemo<JourneyState>(
    () => ({
      cart,
      catalog,
      session,
      cartView,
      setCart,
      setCatalog,
      setSession,
      addToCart,
      removeFromCart,
      adjustQuantity,
      clearCart,
      signInSession,
      signOutSession,
    }),
    [
      cart,
      catalog,
      session,
      cartView,
      addToCart,
      removeFromCart,
      adjustQuantity,
      clearCart,
      signInSession,
      signOutSession,
    ],
  );

  return (
    <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>
  );
}

/** Access the shared journey state. Must be used within a JourneyProvider. */
export function useJourney(): JourneyState {
  const context = useContext(JourneyContext);
  if (context === null) {
    throw new Error("useJourney must be used within a JourneyProvider.");
  }
  return context;
}
