import React, { useEffect, useState } from 'react';
import { ProductCard } from '../components/ProductCard';
import { Product } from '../context/CartContext';
import { Loader2, RefreshCw, AlertCircle } from 'lucide-react';

export const CatalogPage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCatalog = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/products');
      if (!response.ok) {
        throw new Error('Failed to retrieve product catalog.');
      }
      const data = await response.json();
      setProducts(data);
    } catch (err) {
      setError(
        'Unable to connect to the store server. Please verify your connection or try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalog();
  }, []);

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
      {/* Title Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 sm:text-4xl">
          Product Catalog
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          Browse our premium collection of academic merchandise and accessories.
        </p>
      </div>

      {/* Loading State */}
      {loading && (
        <div
          className="flex flex-col items-center justify-center py-20"
          aria-live="polite"
          aria-busy="true"
        >
          <Loader2 className="h-10 w-10 text-indigo-600 animate-spin mb-4" />
          <p className="text-gray-500 font-medium animate-pulse">
            Loading products, please wait...
          </p>
        </div>
      )}

      {/* Recoverable Error State */}
      {!loading && error && (
        <div
          className="bg-red-50 border border-red-200 rounded-xl p-6 text-center max-w-lg mx-auto"
          role="alert"
        >
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-red-800 mb-2">Connection Error</h2>
          <p className="text-red-700 text-sm mb-4 leading-relaxed">{error}</p>
          <button
            onClick={fetchCatalog}
            className="inline-flex items-center gap-2 bg-red-600 text-white font-semibold px-4 py-2 rounded-md hover:bg-red-700 transition-colors shadow-xs cursor-pointer"
            aria-label="Retry loading product catalog"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Retry Connection</span>
          </button>
        </div>
      )}

      {/* Empty Catalog State */}
      {!loading && !error && products.length === 0 && (
        <div className="text-center py-20 bg-white rounded-xl shadow-xs border border-gray-100 max-w-lg mx-auto p-8">
          <AlertCircle className="h-12 w-12 text-indigo-500 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-gray-900 mb-1">Catalog Empty</h2>
          <p className="text-gray-500 text-sm mb-4">
            Our catalog is currently empty. Please check back later.
          </p>
        </div>
      )}

      {/* Catalog Grid */}
      {!loading && !error && products.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </main>
  );
};
