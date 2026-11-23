import { useState, useEffect } from 'react';
import { useApp, Review } from '../context/AppContext';

export default function Moderation() {
  const { fetchModerationReviews, updateReviewStatus, products, user } = useApp();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loadingLocal, setLoadingLocal] = useState<boolean>(false);
  const [filter, setFilter] = useState<'pending' | 'approved' | 'rejected' | 'all'>('pending');

  const loadReviews = async () => {
    setLoadingLocal(true);
    const data = await fetchModerationReviews();
    setReviews(data);
    setLoadingLocal(false);
  };

  useEffect(() => {
    loadReviews();
  }, []);

  const handleStatusUpdate = async (reviewId: number, status: 'approved' | 'rejected') => {
    const success = await updateReviewStatus(reviewId, status);
    if (success) {
      // Refresh the queue locally
      loadReviews();
    }
  };

  const getProductName = (productId: number) => {
    const prod = products.find((p) => p.id === productId);
    return prod ? prod.name : `Product ID: ${productId}`;
  };

  const filteredReviews = reviews.filter((r) => {
    if (filter === 'all') return true;
    return r.status === filter;
  });

  if (user?.username !== 'moderator') {
    return (
      <div className="unauthorized-message">
        <h2>Access Denied</h2>
        <p>Only the moderator user can access this page.</p>
      </div>
    );
  }

  return (
    <section className="moderation-container" aria-labelledby="moderation-heading">
      <h1 id="moderation-heading" className="catalog-title">Moderation Dashboard</h1>
      <p className="moderation-sub">Review and moderate user-submitted reviews. Only approved reviews are shown to catalog visitors.</p>

      <div className="moderation-filters">
        <button
          className={`filter-tab ${filter === 'pending' ? 'active' : ''}`}
          onClick={() => setFilter('pending')}
        >
          Pending ({reviews.filter((r) => r.status === 'pending').length})
        </button>
        <button
          className={`filter-tab ${filter === 'approved' ? 'active' : ''}`}
          onClick={() => setFilter('approved')}
        >
          Approved ({reviews.filter((r) => r.status === 'approved').length})
        </button>
        <button
          className={`filter-tab ${filter === 'rejected' ? 'active' : ''}`}
          onClick={() => setFilter('rejected')}
        >
          Rejected ({reviews.filter((r) => r.status === 'rejected').length})
        </button>
        <button
          className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All ({reviews.length})
        </button>
      </div>

      {loadingLocal ? (
        <div className="loading-spinner">Loading reviews queue...</div>
      ) : filteredReviews.length === 0 ? (
        <div className="empty-moderation">
          <span className="empty-icon" aria-hidden="true">✓</span>
          <p>No reviews found matching the "{filter}" filter.</p>
        </div>
      ) : (
        <div className="moderation-grid">
          {filteredReviews.map((review) => (
            <div key={review.id} className={`moderation-card ${review.status}`}>
              <div className="moderation-card-header">
                <div>
                  <span className="reviewer-badge">{review.username}</span>
                  <span className="review-date">{review.created_at}</span>
                </div>
                <span className={`status-pill ${review.status}`}>{review.status}</span>
              </div>

              <div className="moderation-card-body">
                <h3 className="moderation-product-title">{getProductName(review.product_id)}</h3>
                <div className="stars" aria-label={`Rating: ${review.rating} out of 5 stars`}>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <span key={i} className={i < review.rating ? 'star filled' : 'star'}>★</span>
                  ))}
                </div>
                <p className="moderation-comment">"{review.comment}"</p>

                {review.image_base64 && (
                  <div className="moderation-image-container">
                    <span className="image-label">Attached Image:</span>
                    <img src={review.image_base64} alt="User upload thumbnail" className="moderation-thumbnail" />
                  </div>
                )}
              </div>

              {review.status === 'pending' && (
                <div className="moderation-card-actions">
                  <button
                    className="action-btn approve"
                    onClick={() => handleStatusUpdate(review.id, 'approved')}
                    aria-label={`Approve review ${review.id}`}
                  >
                    Approve
                  </button>
                  <button
                    className="action-btn reject"
                    onClick={() => handleStatusUpdate(review.id, 'rejected')}
                    aria-label={`Reject review ${review.id}`}
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
