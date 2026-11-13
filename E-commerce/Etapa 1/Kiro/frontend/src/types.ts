// Shared domain types mirroring the backend data models (design: Data Models).
// All identifiers and text are in English (Requirement 14.7).

/** A catalog item owned by the backend and served to the frontend. */
export interface Product {
  id: string;
  name: string;
  imageUrl: string;
  description: string;
  price: number;
  available: boolean;
}

/** A product selected into the local, in-memory cart with its quantity. */
export interface CartItem {
  productId: string;
  quantity: number;
}

/** A single resolved line in the derived cart view. */
export interface CartViewLine {
  product: Product;
  quantity: number;
  unitPrice: number;
  lineTotal: number;
}

/** Derived (not stored) cart view used by the Cart and Checkout views. */
export interface CartView {
  items: CartViewLine[];
  total: number;
}

/** Frontend session representation. Holds no password or credential value. */
export interface SessionState {
  active: boolean;
  identity: string | null;
}

/** The credential contract accepted by register/login: identifier + password. */
export interface Credentials {
  identifier: string;
  password: string;
}

/** Cart contents submitted to the non-persistent checkout confirmation. */
export interface CheckoutRequest {
  items: CartItem[];
}

/** A single line in the checkout confirmation summary. */
export interface CheckoutConfirmationLine {
  productId: string;
  name: string;
  unitPrice: number;
  quantity: number;
  lineTotal: number;
}

/** The non-persistent confirmation summary returned by the backend. */
export interface CheckoutConfirmation {
  items: CheckoutConfirmationLine[];
  total: number;
  simulated: true;
}
