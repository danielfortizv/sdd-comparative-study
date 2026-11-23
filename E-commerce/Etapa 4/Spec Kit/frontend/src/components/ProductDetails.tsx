import React, { useEffect, useState, useCallback } from "react";
import { api, Product, Review } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useToast } from "./FeedbackToast";

interface ProductDetailsProps {
  product: Product;
  onBack: () => void;
}

export const ProductDetails: React.FC<ProductDetailsProps> = ({ product, onBack }) => {
  const { token, isAuthenticated } = useAuth();
  const { addItem } = useCart();
  const { showToast } = useToast();

  const [reviews, setReviews] = useState<Review[]>([]);
  const [loadingReviews, setLoadingReviews] = useState<boolean>(true);
  const [reviewsError, setReviewsError] = useState<string | null>(null);

  // Form states
  const [rating, setRating] = useState<number>(5);
  const [comment, setComment] = useState<string>("");
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitSuccess, setSubmitSuccess] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const fetchReviews = useCallback(async () => {
    setLoadingReviews(true);
    setReviewsError(null);
    try {
      const data = await api.getReviews(product.product_id);
      setReviews(data);
    } catch (err: any) {
      setReviewsError(err.message || "Failed to load product reviews.");
    } finally {
      setLoadingReviews(false);
    }
  }, [product.product_id]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const handleAddToCart = () => {
    addItem(product);
    showToast(`Added ${product.name} to your local shopping cart!`, "success");
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        setSubmitError("Image is too large. Max size allowed is 2MB.");
        return;
      }
      setSubmitError(null);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImageBase64(reader.result as string);
      };
      reader.onerror = () => {
        setSubmitError("Failed to read image file.");
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(false);

    if (!comment.trim()) {
      setSubmitError("Comment cannot be empty.");
      setSubmitting(false);
      return;
    }

    try {
      await api.submitReview(token || "", product.product_id, rating, comment, imageBase64);
      setSubmitSuccess(true);
      setComment("");
      setRating(5);
      setImageBase64(null);
      // Reset the file input element in form
      const fileInput = document.getElementById("review-image-input") as HTMLInputElement;
      if (fileInput) {
        fileInput.value = "";
      }
      showToast("Your review has been submitted and is pending moderation.", "success");
    } catch (err: any) {
      setSubmitError(err.message || "Failed to submit review.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="product-details-page" data-testid="product-details-page" style={{ padding: "20px 0" }}>
      <button className="back-to-catalog-btn" onClick={onBack} style={{ marginBottom: "20px", cursor: "pointer", padding: "8px 16px" }}>
        ← Back to Catalog
      </button>

      <div className="product-details-container" style={{ display: "flex", flexWrap: "wrap", gap: "30px", marginBottom: "40px" }}>
        <div className="product-image-large" style={{ flex: "1 1 300px", minHeight: "250px", backgroundColor: "#f0f0f0", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "8px" }}>
          <span style={{ fontSize: "64px" }}>📦</span>
        </div>

        <div className="product-info-panel" style={{ flex: "1 1 400px" }}>
          <h2 style={{ fontSize: "28px", margin: "0 0 10px 0" }}>{product.name}</h2>
          <p style={{ color: "#666", fontSize: "16px", lineHeight: "1.6", marginBottom: "20px" }}>{product.short_description}</p>
          <div className="meta" style={{ display: "flex", gap: "20px", alignItems: "center", marginBottom: "20px" }}>
            <span style={{ fontSize: "24px", fontWeight: "bold", color: "#333" }}>${product.price.toFixed(2)}</span>
            <span style={{ backgroundColor: "#e0f7fa", color: "#006064", padding: "4px 8px", borderRadius: "4px", fontSize: "14px" }}>{product.general_availability}</span>
          </div>
          <button
            className="add-to-cart-btn"
            onClick={handleAddToCart}
            style={{ padding: "12px 24px", fontSize: "16px", cursor: "pointer", backgroundColor: "#007bff", color: "#fff", border: "none", borderRadius: "4px" }}
          >
            Add to Cart
          </button>
        </div>
      </div>

      {/* Reviews Section */}
      <hr style={{ border: "0", borderTop: "1px solid #ddd", margin: "40px 0" }} />

      <div className="reviews-section" style={{ maxWidth: "800px" }}>
        <h3 style={{ fontSize: "22px", marginBottom: "20px" }}>Product Reviews</h3>

        {loadingReviews ? (
          <p>Loading reviews...</p>
        ) : reviewsError ? (
          <p style={{ color: "red" }}>{reviewsError}</p>
        ) : reviews.length === 0 ? (
          <p style={{ color: "#777", fontStyle: "italic", marginBottom: "30px" }}>No reviews have been posted for this product yet.</p>
        ) : (
          <div className="reviews-list" style={{ display: "flex", flexDirection: "column", gap: "20px", marginBottom: "40px" }}>
            {reviews.map((rev) => (
              <div key={rev.review_id} className="review-card" style={{ border: "1px solid #eee", padding: "15px", borderRadius: "6px", backgroundColor: "#fdfdfd" }} data-testid="review-card">
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <span style={{ fontWeight: "bold" }}>{rev.user_id}</span>
                  <span style={{ color: "#ffc107", fontWeight: "bold" }}>
                    {"★".repeat(rev.rating)}
                    {"☆".repeat(5 - rev.rating)}
                  </span>
                </div>
                <p style={{ margin: "0 0 10px 0", color: "#333", lineHeight: "1.5" }}>{rev.comment}</p>
                {rev.image_base64 && (
                  <div className="review-image" style={{ marginTop: "10px" }}>
                    <img
                      src={rev.image_base64}
                      alt="Review attachment"
                      style={{ maxWidth: "200px", maxHeight: "150px", objectFit: "contain", borderRadius: "4px", border: "1px solid #ddd" }}
                    />
                  </div>
                )}
                <div style={{ fontSize: "12px", color: "#999", marginTop: "10px" }}>
                  Posted on: {new Date(rev.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Submit Review Form */}
        <div className="review-form-container" style={{ border: "1px solid #ddd", padding: "20px", borderRadius: "8px", backgroundColor: "#fafafa" }}>
          <h4 style={{ fontSize: "18px", margin: "0 0 15px 0" }}>Write a Customer Review</h4>

          {!isAuthenticated ? (
            <p style={{ color: "#555", fontStyle: "italic", margin: 0 }}>Please sign in to write a review.</p>
          ) : (
            <form onSubmit={handleSubmitReview} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
              {submitSuccess && (
                <div style={{ backgroundColor: "#d4edda", color: "#155724", padding: "10px", borderRadius: "4px", fontSize: "14px" }}>
                  Your review has been submitted and is pending moderation.
                </div>
              )}
              {submitError && (
                <div style={{ backgroundColor: "#f8d7da", color: "#721c24", padding: "10px", borderRadius: "4px", fontSize: "14px" }}>
                  {submitError}
                </div>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                <label htmlFor="review-rating" style={{ fontWeight: "bold", fontSize: "14px" }}>Rating</label>
                <select
                  id="review-rating"
                  value={rating}
                  onChange={(e) => setRating(parseInt(e.target.value))}
                  style={{ padding: "8px", borderRadius: "4px", border: "1px solid #ccc", width: "120px" }}
                >
                  <option value={5}>5 Stars</option>
                  <option value={4}>4 Stars</option>
                  <option value={3}>3 Stars</option>
                  <option value={2}>2 Stars</option>
                  <option value={1}>1 Star</option>
                </select>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                <label htmlFor="review-comment" style={{ fontWeight: "bold", fontSize: "14px" }}>Review Comment</label>
                <textarea
                  id="review-comment"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="What did you like or dislike about this product?"
                  rows={4}
                  required
                  style={{ padding: "10px", borderRadius: "4px", border: "1px solid #ccc", fontFamily: "inherit" }}
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                <label htmlFor="review-image-input" style={{ fontWeight: "bold", fontSize: "14px" }}>Attach Image (Optional)</label>
                <input
                  type="file"
                  id="review-image-input"
                  accept="image/*"
                  onChange={handleImageChange}
                  style={{ fontSize: "14px" }}
                />
                {imageBase64 && (
                  <div style={{ marginTop: "10px" }}>
                    <p style={{ fontSize: "12px", margin: "0 0 5px 0", color: "#666" }}>Preview:</p>
                    <img
                      src={imageBase64}
                      alt="Upload preview"
                      style={{ maxWidth: "150px", maxHeight: "100px", objectFit: "contain", border: "1px solid #ccc", borderRadius: "4px" }}
                    />
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={submitting}
                style={{
                  alignSelf: "flex-start",
                  padding: "10px 20px",
                  fontSize: "14px",
                  cursor: "pointer",
                  backgroundColor: "#28a745",
                  color: "#fff",
                  border: "none",
                  borderRadius: "4px",
                  fontWeight: "bold"
                }}
              >
                {submitting ? "Submitting..." : "Submit Review"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
