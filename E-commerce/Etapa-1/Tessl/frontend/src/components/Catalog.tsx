import { useState } from 'react';
import { useApp, Product } from '../context/AppContext';

function ProductCard({ product }: { product: Product }) {
  const { addToCart } = useApp();
  const [imageError, setImageError] = useState(false);

  return (
    <div className="product-card">
      <div className="product-image-container">
        {imageError ? (
          <div className="image-fallback">
            <span className="image-fallback-icon" aria-hidden="true">📦</span>
            <span>Image Unavailable</span>
          </div>
        ) : (
          <img
            src={product.image_url}
            alt={product.name}
            className="product-image"
            onError={() => setImageError(true)}
          />
        )}
        <span className={`availability-tag ${product.availability ? 'available' : 'out-of-stock'}`}>
          {product.availability ? 'Available' : 'Out of Stock'}
        </span>
      </div>

      <div className="product-details">
        <h2 className="product-name">{product.name}</h2>
        <p className="product-desc">{product.description}</p>
        <div className="product-footer">
          <span className="product-price">${product.price.toFixed(2)}</span>
          <button
            className="nav-btn primary"
            onClick={() => addToCart(product)}
            disabled={!product.availability}
            aria-label={`Add ${product.name} to cart`}
          >
            {product.availability ? 'Add to Cart' : 'Out of Stock'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Catalog() {
  const { products, loading } = useApp();

  if (loading && products.length === 0) {
    return <div className="loading-spinner">Loading product catalog...</div>;
  }

  return (
    <section aria-labelledby="catalog-heading">
      <h1 id="catalog-heading" className="catalog-title">Product Catalog</h1>
      {products.length === 0 ? (
        <p>No products available at the moment.</p>
      ) : (
        <div className="catalog-grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </section>
  );
}
