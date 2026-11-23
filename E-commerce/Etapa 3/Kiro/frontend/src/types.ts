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
  /**
   * Stage 2 (Assumption A5): whether the signed-in account is a moderator,
   * used to gate the moderation view. Optional/false for regular customers so
   * Stage 1 behavior is unchanged.
   */
  isModerator?: boolean;
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

// --- Stage 2: reviews with images and moderation ----------------------------
// All identifiers and text are in English (Requirement 9.7). These mirror the
// backend review models and camelCase HTTP/JSON shapes.

/** The moderation lifecycle state of a review (Assumption A4). */
export type ModerationState = "pending" | "approved" | "rejected";

/** An attached review image as surfaced to the frontend. */
export interface ReviewImage {
  id: string;
  /** Relative URL to fetch the image bytes (`/reviews/images/{id}`). */
  imageUrl: string;
  mediaType: string;
}

/** A single image to submit with a review (base64-encoded, Assumption A3). */
export interface ReviewImageInput {
  mediaType: string;
  dataBase64: string;
}

/** A product review as returned by the backend. */
export interface Review {
  id: string;
  productId: string;
  /** The authoring account's non-sensitive identity (never a credential). */
  authorIdentity: string;
  rating: number;
  title: string | null;
  text: string;
  images: ReviewImage[];
  moderationState: ModerationState;
}

/** The review a customer submits for a product. */
export interface ReviewSubmission {
  rating: number;
  text: string;
  title?: string | null;
  images: ReviewImageInput[];
}

/** Aggregate rating for a product's visible (approved) reviews. */
export interface RatingSummary {
  count: number;
  average: number;
}

/** Public reviews payload for a product. */
export interface ProductReviews {
  reviews: Review[];
  summary: RatingSummary;
  /** The requester's own non-approved review for this product, if any. */
  ownReview: Review | null;
}
