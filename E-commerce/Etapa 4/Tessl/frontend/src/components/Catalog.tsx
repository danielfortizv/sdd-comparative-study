import { useState, useEffect } from 'react';
import { useApp, Product, Review } from '../context/AppContext';

interface ProductCardProps {
  product: Product;
  onViewReviews: (product: Product) => void;
}

function ProductCard({ product, onViewReviews }: ProductCardProps) {
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
          <div className="product-card-actions">
            <button
              className="nav-btn secondary"
              onClick={() => onViewReviews(product)}
              aria-label={`View reviews for ${product.name}`}
            >
              Reviews
            </button>
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
    </div>
  );
}

interface ReviewsModalProps {
  product: Product;
  onClose: () => void;
}

function ProductReviewsModal({ product, onClose }: ReviewsModalProps) {
  const { fetchProductReviews, submitReview, user, setView, loading } = useApp();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState<boolean>(false);

  // Form states
  const [rating, setRating] = useState<number>(5);
  const [comment, setComment] = useState<string>('');
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [hoverRating, setHoverRating] = useState<number>(0);
  const [imageError, setImageError] = useState<string | null>(null);

  const loadProductReviews = async () => {
    setReviewsLoading(true);
    const data = await fetchProductReviews(product.id);
    setReviews(data);
    setReviewsLoading(false);
  };

  useEffect(() => {
    loadProductReviews();
  }, [product.id]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setImageError(null);
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setImageError('Please upload an image file (e.g., png, jpg, jpeg).');
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      setImageError('File size exceeds the 2MB limit.');
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      setImageBase64(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleClearImage = () => {
    setImageBase64(null);
    setImageError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!comment.trim()) return;

    const success = await submitReview(product.id, rating, comment, imageBase64);
    if (success) {
      setRating(5);
      setComment('');
      setImageBase64(null);
      // Reload reviews (note: newly submitted reviews are pending, so they won't appear instantly to regular users)
      loadProductReviews();
    }
  };

  // Calculate average rating
  const averageRating = reviews.length > 0 
    ? (reviews.reduce((acc, r) => acc + r.rating, 0) / reviews.length).toFixed(1)
    : null;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-product-title">
      <div className="modal-content">
        <header className="modal-header">
          <h2 id="modal-product-title">Reviews for {product.name}</h2>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">&times;</button>
        </header>

        <div className="modal-body">
          {/* Product Summary section */}
          <div className="modal-product-summary">
            <div className="summary-info">
              <p className="summary-desc">{product.description}</p>
              <div className="summary-metrics">
                <span className="summary-price">${product.price.toFixed(2)}</span>
                {averageRating && (
                  <span className="summary-rating-badge">
                    ⭐ {averageRating} / 5.0 ({reviews.length} review{reviews.length !== 1 ? 's' : ''})
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="reviews-section-grid">
            {/* Reviews List */}
            <div className="reviews-list-container">
              <h3>Customer Reviews</h3>
              {reviewsLoading ? (
                <div className="loading-spinner">Loading reviews...</div>
              ) : reviews.length === 0 ? (
                <div className="empty-reviews-state">
                  <p>No approved reviews for this product yet.</p>
                  <p className="empty-reviews-sub">Be the first to share your thoughts!</p>
                </div>
              ) : (
                <div className="reviews-list">
                  {reviews.map((rev) => (
                    <div key={rev.id} className="review-item">
                      <div className="review-item-header">
                        <span className="review-author">{rev.username}</span>
                        <span className="review-date">{rev.created_at}</span>
                      </div>
                      <div className="review-stars" aria-label={`Rating: ${rev.rating} out of 5 stars`}>
                        {Array.from({ length: 5 }).map((_, idx) => (
                          <span key={idx} className={idx < rev.rating ? 'star filled' : 'star'}>★</span>
                        ))}
                      </div>
                      <p className="review-comment">"{rev.comment}"</p>
                      {rev.image_base64 && (
                        <div className="review-image-attachment">
                          <img src={rev.image_base64} alt={`Review by ${rev.username}`} className="attached-review-img" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Submit Form */}
            <div className="write-review-container">
              <h3>Write a Product Review</h3>
              {user ? (
                <form onSubmit={handleSubmit} className="review-form">
                  <div className="form-group">
                    <label>Your Rating:</label>
                    <div className="star-rating-input" onMouseLeave={() => setHoverRating(0)}>
                      {Array.from({ length: 5 }).map((_, idx) => {
                        const starVal = idx + 1;
                        return (
                          <button
                            key={idx}
                            type="button"
                            className={`star-btn ${(hoverRating || rating) >= starVal ? 'filled' : ''}`}
                            onClick={() => setRating(starVal)}
                            onMouseEnter={() => setHoverRating(starVal)}
                            aria-label={`Rate ${starVal} out of 5 stars`}
                          >
                            ★
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="review-comment-input">Review Comment:</label>
                    <textarea
                      id="review-comment-input"
                      rows={4}
                      placeholder="Share your experience using this product. Be honest and descriptive..."
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      required
                    ></textarea>
                  </div>

                  <div className="form-group">
                    <label>Attach an Image (Optional, max 2MB):</label>
                    <div className="file-upload-wrapper">
                      <input
                        type="file"
                        id="review-image-file"
                        accept="image/*"
                        onChange={handleFileChange}
                        className="file-input-hidden"
                      />
                      <label htmlFor="review-image-file" className="file-upload-label">
                        Choose Image File...
                      </label>
                      {imageBase64 && (
                        <div className="selected-image-preview">
                          <img src={imageBase64} alt="Upload preview" className="upload-preview-img" />
                          <button type="button" className="clear-image-btn" onClick={handleClearImage}>&times;</button>
                        </div>
                      )}
                    </div>
                    {imageError && <p className="field-error-message">{imageError}</p>}
                  </div>

                  <button
                    type="submit"
                    className="nav-btn primary submit-review-btn"
                    disabled={loading || !comment.trim()}
                  >
                    {loading ? 'Submitting...' : 'Submit Review'}
                  </button>
                </form>
              ) : (
                <div className="auth-prompt-card">
                  <p>You must be signed in to submit a review.</p>
                  <button className="nav-btn primary" onClick={() => { onClose(); setView('auth'); }}>
                    Sign In Now
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Catalog() {
  const { products, loading } = useApp();
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

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
            <ProductCard
              key={product.id}
              product={product}
              onViewReviews={(prod) => setSelectedProduct(prod)}
            />
          ))}
        </div>
      )}

      {selectedProduct && (
        <ProductReviewsModal
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
        />
      )}
    </section>
  );
}
