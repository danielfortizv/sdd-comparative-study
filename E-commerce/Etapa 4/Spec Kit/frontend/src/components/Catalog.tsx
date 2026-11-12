import React, { useEffect, useState } from "react";
import { api, Product } from "../services/api";
import { useCart } from "../context/CartContext";
import { useToast } from "./FeedbackToast";
import { LoadingFallback, EmptyCatalogFallback, ErrorFallback } from "./StateFallbacks";
import { ProductDetails } from "./ProductDetails";

export const Catalog: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  const { addItem } = useCart();
  const { showToast } = useToast();

  const fetchCatalog = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProducts();
      setProducts(data);
    } catch (err: any) {
      setError(err.message || "Failed to load product catalog.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalog();
  }, []);

  const handleAddToCart = (product: Product) => {
    addItem(product);
    showToast(`Added ${product.name} to your local shopping cart!`, "success");
  };

  if (loading) {
    return <LoadingFallback />;
  }

  if (error) {
    return <ErrorFallback message={error} onRetry={fetchCatalog} />;
  }

  if (products.length === 0) {
    return <EmptyCatalogFallback />;
  }

  if (selectedProduct) {
    return <ProductDetails product={selectedProduct} onBack={() => setSelectedProduct(null)} />;
  }

  return (
    <div className="catalog-container" data-testid="catalog">
      <h2 className="section-title">Product Catalog</h2>
      <div className="product-grid">
        {products.map((product) => (
          <div key={product.product_id} className="product-card" data-testid="product-card">
            {/* Representative Image (simple styling fallback representation) */}
            <div className="product-image-container" onClick={() => setSelectedProduct(product)} style={{ cursor: "pointer" }}>
              <div className="product-image-placeholder">
                <span className="image-icon">📦</span>
              </div>
            </div>
            <div className="product-details">
              <h3 className="product-name" onClick={() => setSelectedProduct(product)} style={{ cursor: "pointer", textDecoration: "underline" }}>
                {product.name}
              </h3>
              <p className="product-description">{product.short_description}</p>
              <div className="product-meta">
                <span className="product-price">${product.price.toFixed(2)}</span>
                <span className="product-availability">{product.general_availability}</span>
              </div>
              <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                <button
                  className="add-to-cart-btn"
                  onClick={() => handleAddToCart(product)}
                  aria-label={`Add ${product.name} to cart`}
                  style={{ flex: 1 }}
                >
                  Add to Cart
                </button>
                <button
                  className="view-details-btn"
                  onClick={() => setSelectedProduct(product)}
                  aria-label={`View reviews for ${product.name}`}
                  style={{ flex: 1, padding: "8px 12px", cursor: "pointer", backgroundColor: "#6c757d", color: "#fff", border: "none", borderRadius: "4px" }}
                >
                  View Reviews
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
export default Catalog;
