import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { Star, ArrowLeft, Camera, Loader2, CheckCircle, ShoppingCart } from 'lucide-react';

interface Review {
  id: number;
  product_id: number;
  user_id: string;
  rating: number;
  comment: string;
  image_data: string | null;
  status: string;
  created_at: string;
}

interface ProductDetail {
  id: number;
  name: string;
  image_url: string;
  description: string;
  price: number;
  is_available: boolean;
  average_rating: number | null;
}

export const ProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, sessionToken } = useAuth();
  const { addToCart } = useCart();

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [addedFeedback, setAddedFeedback] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchProductAndReviews = async () => {
    setLoading(true);
    setReviewsLoading(true);
    setError(null);
    try {
      // 1. Fetch Product details
      const prodRes = await fetch(`http://127.0.0.1:8000/api/products/${id}`);
      if (!prodRes.ok) {
        if (prodRes.status === 404) {
          throw new Error('Product not found.');
        }
        throw new Error('Failed to load product details.');
      }
      const prodData = await prodRes.json();
      setProduct(prodData);
      setLoading(false);

      // 2. Fetch approved reviews
      const revRes = await fetch(`http://127.0.0.1:8000/api/products/${id}/reviews`);
      if (revRes.ok) {
        const revData = await revRes.json();
        setReviews(revData);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred while fetching details.');
      setLoading(false);
    } finally {
      setReviewsLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchProductAndReviews();
    }
  }, [id]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 1024 * 1024) {
      setSubmitError('Image file is too large. Please select an image under 1MB.');
      return;
    }

    setSubmitError(null);

    // Create a local object URL for instant preview
    const objectUrl = URL.createObjectURL(file);
    setImagePreview(objectUrl);

    // Convert file to Base64
    const reader = new FileReader();
    reader.onloadend = () => {
      setImageBase64(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const clearImage = () => {
    setImageBase64(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAddToCart = () => {
    if (!product || !product.is_available) return;
    addToCart({
      id: product.id,
      name: product.name,
      price: product.price,
      image_url: product.image_url,
      description: product.description,
      is_available: product.is_available,
    });
    setAddedFeedback(true);
    setTimeout(() => {
      setAddedFeedback(false);
    }, 1500);
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) return;

    setSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(false);

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/products/${id}/reviews`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({
          rating,
          comment,
          image_data: imageBase64,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit review.');
      }

      setSubmitSuccess(true);
      setComment('');
      clearImage();
      setRating(5);
      // Let success notification show, reviews won't list the new review until approved anyway!
    } catch (err: any) {
      setSubmitError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderStars = (count: number) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`h-5 w-5 ${
              star <= count ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'
            }`}
          />
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-20" aria-live="polite">
        <Loader2 className="h-10 w-10 text-indigo-600 animate-spin mb-4" />
        <p className="text-gray-500 font-medium animate-pulse">Loading product details...</p>
      </div>
    );
  }

  if (error || !product) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-12 flex-1">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <h2 className="text-xl font-bold text-red-800 mb-2">Error</h2>
          <p className="text-red-700 mb-6">{error || 'Product not found.'}</p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 bg-indigo-600 text-white font-semibold px-4 py-2 rounded-md hover:bg-indigo-700 transition-colors cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Return to Catalog</span>
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
      {/* Back Button */}
      <div className="mb-6">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-indigo-600 font-medium transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Catalog</span>
        </Link>
      </div>

      {/* Split details layout */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-10 bg-white rounded-2xl border border-gray-100 shadow-sm p-6 md:p-8 mb-10">
        {/* Product Image */}
        <div className="bg-gray-50 rounded-xl overflow-hidden flex items-center justify-center h-96 relative border border-gray-150">
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover"
          />
          {!product.is_available && (
            <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center">
              <span className="text-white font-bold tracking-wide uppercase px-4 py-2 bg-red-600 rounded-md text-sm">
                Out of Stock
              </span>
            </div>
          )}
        </div>

        {/* Product Details info */}
        <div className="flex flex-col justify-between">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900 mb-2">{product.name}</h1>
            
            {/* Rating summary */}
            <div className="flex items-center gap-3 mb-6">
              {product.average_rating ? (
                <>
                  {renderStars(Math.round(product.average_rating))}
                  <span className="text-sm font-bold text-gray-700 bg-yellow-50 border border-yellow-200 px-2.5 py-0.5 rounded-full">
                    {product.average_rating.toFixed(1)} / 5.0
                  </span>
                  <span className="text-xs text-gray-400">
                    ({reviews.length} {reviews.length === 1 ? 'review' : 'reviews'})
                  </span>
                </>
              ) : (
                <>
                  {renderStars(0)}
                  <span className="text-xs text-gray-400">No approved reviews yet</span>
                </>
              )}
            </div>

            <p className="text-3xl font-extrabold text-indigo-600 mb-6">
              ${product.price.toFixed(2)}
            </p>

            <div className="border-t border-gray-100 pt-6 mb-6">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Description
              </h2>
              <p className="text-gray-600 leading-relaxed text-sm">{product.description}</p>
            </div>
          </div>

          <div>
            <button
              onClick={handleAddToCart}
              disabled={!product.is_available}
              className={`w-full md:w-auto flex items-center justify-center gap-2 py-3 px-8 rounded-lg font-bold text-sm transition-all shadow-md ${
                !product.is_available
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : addedFeedback
                  ? 'bg-green-600 text-white'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700 active:scale-98 cursor-pointer'
              }`}
            >
              {addedFeedback ? (
                <>
                  <CheckCircle className="h-5 w-5 animate-bounce" />
                  <span>Added to Cart!</span>
                </>
              ) : (
                <>
                  <ShoppingCart className="h-5 w-5" />
                  <span>Add to Cart</span>
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      {/* Reviews section */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        {/* Left Column: approved reviews list */}
        <div className="lg:col-span-2">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Customer Reviews</h2>

          {reviewsLoading ? (
            <div className="flex py-10 justify-center">
              <Loader2 className="h-6 w-6 text-indigo-600 animate-spin" />
            </div>
          ) : reviews.length === 0 ? (
            <div className="bg-gray-50 border border-dashed border-gray-200 rounded-xl p-8 text-center">
              <p className="text-gray-500 font-medium mb-1">No reviews yet</p>
              <p className="text-xs text-gray-400">
                Be the first to share your thoughts about this product!
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {reviews.map((review) => (
                <div
                  key={review.id}
                  className="bg-white rounded-xl border border-gray-100 shadow-2xs p-5 flex flex-col md:flex-row gap-5"
                >
                  <div className="flex-1">
                    <div className="flex items-center justify-between gap-4 mb-2">
                      <span className="font-bold text-gray-900 text-sm">{review.user_id}</span>
                      <span className="text-xs text-gray-400">
                        {new Date(review.created_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </span>
                    </div>

                    <div className="mb-3">{renderStars(review.rating)}</div>

                    <p className="text-gray-600 text-sm leading-relaxed">{review.comment}</p>
                  </div>

                  {review.image_data && (
                    <div className="w-24 h-24 md:w-32 md:h-32 bg-gray-50 rounded-lg overflow-hidden flex-shrink-0 border border-gray-150">
                      <img
                        src={review.image_data}
                        alt="User review attachment"
                        className="w-full h-full object-cover hover:scale-105 transition-transform"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: submit review form */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Write a Review</h2>

          {isAuthenticated ? (
            <form
              onSubmit={handleReviewSubmit}
              className="bg-white border border-gray-100 shadow-sm rounded-xl p-5"
            >
              {/* Star Rating Selector */}
              <div className="mb-4">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Overall Rating
                </label>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRating(star)}
                      className="p-1 hover:scale-110 transition-transform cursor-pointer"
                      aria-label={`Rate ${star} out of 5 stars`}
                    >
                      <Star
                        className={`h-8 w-8 ${
                          star <= rating
                            ? 'text-yellow-400 fill-yellow-400'
                            : 'text-gray-300 hover:text-yellow-300'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Comment text area */}
              <div className="mb-4">
                <label
                  htmlFor="comment"
                  className="block text-sm font-semibold text-gray-700 mb-2"
                >
                  Review Comments
                </label>
                <textarea
                  id="comment"
                  rows={4}
                  required
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="What did you like or dislike? English-only comments..."
                  className="w-full rounded-md border border-gray-200 p-2.5 text-sm focus:outline-hidden focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              {/* Image Uploader */}
              <div className="mb-5">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Add Photo (Optional)
                </label>
                
                {imagePreview ? (
                  <div className="relative inline-block">
                    <img
                      src={imagePreview}
                      alt="Upload preview"
                      className="w-32 h-32 object-cover rounded-lg border border-gray-200"
                    />
                    <button
                      type="button"
                      onClick={clearImage}
                      className="absolute -top-2 -right-2 bg-red-600 text-white rounded-full p-1 shadow-md hover:bg-red-700 transition-colors"
                      aria-label="Remove uploaded image"
                    >
                      <Star className="h-4 w-4 rotate-45" />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex flex-col items-center justify-center border-2 border-dashed border-gray-200 rounded-lg p-5 w-full hover:bg-gray-50 hover:border-indigo-500 transition-colors cursor-pointer"
                  >
                    <Camera className="h-6 w-6 text-gray-400 mb-1" />
                    <span className="text-xs font-medium text-gray-600">Upload an image</span>
                    <span className="text-[10px] text-gray-400 mt-1">PNG, JPG up to 1MB</span>
                  </button>
                )}
                
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleImageChange}
                  accept="image/*"
                  className="hidden"
                />
              </div>

              {/* Submit Error */}
              {submitError && (
                <div className="mb-4 text-xs font-semibold text-red-600 bg-red-50 border border-red-150 p-3 rounded-md">
                  {submitError}
                </div>
              )}

              {/* Submit Success Notification */}
              {submitSuccess && (
                <div className="mb-4 text-xs font-semibold text-green-700 bg-green-50 border border-green-150 p-3 rounded-md flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span>Review submitted successfully! It is pending moderator approval.</span>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2.5 bg-indigo-600 text-white font-semibold text-sm rounded-md hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:bg-indigo-400 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Submitting Review...</span>
                  </>
                ) : (
                  <span>Submit Review</span>
                )}
              </button>
            </form>
          ) : (
            <div className="bg-gray-50 border border-gray-150 rounded-xl p-5 text-center">
              <p className="text-sm text-gray-600 mb-4 font-medium">
                Want to review this product?
              </p>
              <Link
                to="/login"
                className="inline-block bg-indigo-600 text-white font-semibold text-sm px-6 py-2 rounded-md hover:bg-indigo-700 transition-colors"
              >
                Sign In to Review
              </Link>
            </div>
          )}
        </div>
      </section>
    </main>
  );
};
