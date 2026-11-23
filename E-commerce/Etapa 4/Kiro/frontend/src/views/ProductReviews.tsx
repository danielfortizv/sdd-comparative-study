// Product reviews display (Stage 2, design: Frontend Components —
// ProductReviews).
//
// For a given product, loads and displays the approved reviews and the rating
// summary (R4.1, R4.3). Shows each review's rating, optional title, text
// (rendered as text by React's default escaping, R6.2), the non-sensitive
// author identity (R5.4), and attached images with descriptive alt text
// (R2.6, R8.4). Shows a no-reviews empty state (R4.4) and loading/error
// states (R7.1, R7.3). It also surfaces the signed-in author's own pending or
// rejected submission so they can see its state (R4.6), and embeds the review
// submission form for an identified customer.

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "../api/client";
import type { ProductReviews as ProductReviewsData, Review } from "../types";
import { ReviewForm } from "./ReviewForm";

/** Render a rating as an accessible star string plus the numeric value. */
function RatingStars({ rating }: { rating: number }) {
  const rounded = Math.round(rating);
  const label = `Rating: ${rating} out of 5`;
  return (
    <span aria-label={label} data-testid="review-rating">
      {"★".repeat(rounded)}
      {"☆".repeat(Math.max(0, 5 - rounded))} ({rating})
    </span>
  );
}

function ReviewCard({ review }: { review: Review }) {
  return (
    <li className="review-card" data-testid={`review-${review.id}`}>
      <RatingStars rating={review.rating} />
      {review.title && (
        <h5 data-testid="review-title">{review.title}</h5>
      )}
      {/* Rendered as text through React escaping, so stored markup is inert
          (R6.2). */}
      <p data-testid="review-text">{review.text}</p>
      <p className="review-author" data-testid="review-author">
        By {review.authorIdentity}
      </p>
      {review.images.length > 0 && (
        <ul className="review-images" aria-label="Review images">
          {review.images.map((image, index) => (
            <li key={image.id}>
              <img
                src={apiClient.reviewImageUrl(image.imageUrl)}
                alt={`Image ${index + 1} for the review by ${review.authorIdentity}`}
                data-testid="review-image"
              />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function ProductReviews({ productId }: { productId: string }) {
  const [data, setData] = useState<ProductReviewsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiClient.listProductReviews(productId));
    } catch {
      setError("Reviews could not be loaded. Please try again later.");
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section
      aria-labelledby={`reviews-heading-${productId}`}
      className="product-reviews"
    >
      <h4 id={`reviews-heading-${productId}`}>Reviews</h4>

      {loading && (
        <p role="status" data-testid="reviews-loading">
          Loading reviews…
        </p>
      )}

      {!loading && error && (
        <p role="alert" data-testid="reviews-error">
          {error}
        </p>
      )}

      {!loading && !error && data && (
        <>
          {data.summary.count > 0 ? (
            <p data-testid="rating-summary">
              {data.summary.average} average from {data.summary.count} review
              {data.summary.count === 1 ? "" : "s"}.
            </p>
          ) : (
            <p data-testid="reviews-empty-state">
              There are no reviews yet. Be the first to review this product.
            </p>
          )}

          {data.reviews.length > 0 && (
            <ul className="review-list" aria-label="Approved reviews">
              {data.reviews.map((review) => (
                <ReviewCard key={review.id} review={review} />
              ))}
            </ul>
          )}

          {/* The author's own non-approved submission state (R4.6). */}
          {data.ownReview && (
            <p data-testid="own-review-state">
              Your review is {data.ownReview.moderationState}.
            </p>
          )}

          <ReviewForm productId={productId} onSubmitted={() => void load()} />
        </>
      )}
    </section>
  );
}
