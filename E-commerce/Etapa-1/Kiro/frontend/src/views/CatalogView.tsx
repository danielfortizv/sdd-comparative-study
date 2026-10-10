// Catalog view (design: Frontend Components — Catalog).
//
// Presents the product list as the initial view (R1.2), reachable without any
// authentication (R1.1) — no auth gating happens here. For each product it
// shows the name, one representative image, a short description, the price, and
// a general availability indication (R1.3). An optional expanded product view
// shows the same commercial information as the list entry (R1.4). Each product
// offers an add action that places it in the shared cart (R2.1).
//
// The catalog is loaded on mount from the backend and stored in the shared
// journey state so the Cart and Checkout resolve the same demonstration product
// data by identity (R1.5, R11.1). Basic loading and request-failure states are
// handled here; broader cross-cutting polish is task 14.1.

import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";
import { useJourney } from "../state/JourneyState";
import type { Product } from "../types";

/** Format a numeric price using the demonstration currency conventions. */
function formatPrice(price: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(price);
}

/** Human-readable availability indication for a product (R1.3). */
function availabilityLabel(available: boolean): string {
  return available ? "Available" : "Unavailable";
}

/** A single catalog product entry with an optional expanded detail panel. */
function ProductCard({
  product,
  onAdd,
}: {
  product: Product;
  onAdd: (productId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const price = formatPrice(product.price);
  const availability = availabilityLabel(product.available);
  const detailsId = `product-details-${product.id}`;

  return (
    <li className="product-card" aria-labelledby={`product-name-${product.id}`}>
      <h3 id={`product-name-${product.id}`}>{product.name}</h3>
      {/* Meaningful alt text = product name for accessibility (R13.2, R13.3). */}
      <img src={product.imageUrl} alt={product.name} />
      <p className="product-description">{product.description}</p>
      <p className="product-price">{price}</p>
      <p className="product-availability">{availability}</p>
      <div className="product-actions">
        <button type="button" onClick={() => onAdd(product.id)}>
          Add to cart
        </button>
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={detailsId}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Hide details" : "View details"}
        </button>
      </div>

      {/* Expanded product view: shows the SAME commercial fields as the list
          entry, reusing the loaded product so identity stays consistent
          (R1.4, R1.5, R11.1). */}
      {expanded && (
        <div id={detailsId} className="product-details">
          <h4>{product.name}</h4>
          <img src={product.imageUrl} alt={product.name} />
          <p className="product-description">{product.description}</p>
          <p className="product-price">{price}</p>
          <p className="product-availability">{availability}</p>
        </div>
      )}
    </li>
  );
}

export function CatalogView() {
  const { catalog, setCatalog, addToCart } = useJourney();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const products = await apiClient.listProducts();
        if (!cancelled) {
          setCatalog(products);
        }
      } catch {
        if (!cancelled) {
          setError(
            "The catalog could not be loaded. Please try again later.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [setCatalog]);

  const hasProducts = useMemo(() => catalog.length > 0, [catalog]);

  return (
    <section aria-labelledby="catalog-heading">
      <h2 id="catalog-heading">Catalog</h2>

      {loading && (
        <p role="status" data-testid="catalog-loading">
          Loading catalog…
        </p>
      )}

      {!loading && error && (
        <p role="alert" data-testid="catalog-error">
          {error}
        </p>
      )}

      {!loading && !error && !hasProducts && (
        <p role="status" data-testid="catalog-empty-state">
          No products are available right now. Please check back later.
        </p>
      )}

      {!loading && !error && hasProducts && (
        <ul className="product-list">
          {catalog.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onAdd={addToCart}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
