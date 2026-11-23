import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Star, Check, X, Loader2, AlertTriangle, Shield } from 'lucide-react';

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

interface Product {
  id: number;
  name: string;
}

export const ModerationPage: React.FC = () => {
  const { isAuthenticated, accountIdentifier, sessionToken } = useAuth();
  const navigate = useNavigate();

  const [reviews, setReviews] = useState<Review[]>([]);
  const [productsMap, setProductsMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actioningId, setActioningId] = useState<number | null>(null);

  useEffect(() => {
    // 1. Authorization guard: Only exactly 'moderator' can access this
    if (!isAuthenticated || accountIdentifier !== 'moderator') {
      navigate('/', { replace: true });
      return;
    }

    const fetchModerationData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch products first to display names instead of IDs
        const prodRes = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8005'}/api/products`);
        let prodMap: Record<number, string> = {};
        if (prodRes.ok) {
          const products: Product[] = await prodRes.json();
          products.forEach((p) => {
            prodMap[p.id] = p.name;
          });
          setProductsMap(prodMap);
        }

        // Fetch pending reviews
        const revRes = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8005'}/api/moderation/reviews`, {
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
          },
        });

        if (!revRes.ok) {
          if (revRes.status === 403) {
            throw new Error('Access denied. You do not have permission to access moderation.');
          }
          throw new Error('Failed to retrieve reviews for moderation.');
        }

        const revData = await revRes.json();
        setReviews(revData);
      } catch (err: any) {
        setError(err.message || 'An unexpected error occurred.');
      } finally {
        setLoading(false);
      }
    };

    fetchModerationData();
  }, [isAuthenticated, accountIdentifier, sessionToken, navigate]);

  const handleAction = async (reviewId: number, action: 'approve' | 'reject') => {
    setActioningId(reviewId);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8005'}/api/moderation/reviews/${reviewId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({ action }),
      });

      if (!response.ok) {
        throw new Error(`Failed to ${action} review.`);
      }

      // Remove from local list
      setReviews((prev) => prev.filter((r) => r.id !== reviewId));
    } catch (err: any) {
      alert(err.message || 'Action failed.');
    } finally {
      setActioningId(null);
    }
  };

  const renderStars = (count: number) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`h-4 w-4 ${
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
        <p className="text-gray-500 font-medium animate-pulse">Loading moderation workspace...</p>
      </div>
    );
  }

  if (error) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-12 flex-1">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-red-800 mb-2">Access Error</h2>
          <p className="text-red-700 mb-6">{error}</p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 bg-indigo-600 text-white font-semibold px-4 py-2 rounded-md hover:bg-indigo-700 transition-colors cursor-pointer"
          >
            <span>Return to Catalog</span>
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
      {/* Page Header */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-150 pb-5">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 flex items-center gap-2">
            <Shield className="h-8 w-8 text-indigo-600" />
            <span>Moderation Dashboard</span>
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Review submitted feedback, check images, and approve or reject comments.
          </p>
        </div>
        <div className="bg-indigo-50 border border-indigo-200 rounded-full px-4 py-1.5 self-start text-xs font-bold text-indigo-800 flex items-center gap-1.5">
          <span className="h-2 w-2 bg-green-500 rounded-full animate-ping" />
          <span>Session: Moderator Account</span>
        </div>
      </div>

      {/* Pending Reviews Queue */}
      {reviews.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-gray-100 shadow-2xs max-w-lg mx-auto p-8">
          <Check className="h-12 w-12 text-green-500 mx-auto mb-3 bg-green-55 rounded-full p-2.5" />
          <h2 className="text-lg font-bold text-gray-900 mb-1">Queue Clear!</h2>
          <p className="text-gray-500 text-sm">
            There are no reviews currently awaiting moderation. Excellent work!
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Pending Queue ({reviews.length} awaiting action)
          </h2>
          
          <div className="grid grid-cols-1 gap-6">
            {reviews.map((review) => (
              <div
                key={review.id}
                className="bg-white rounded-xl border border-gray-150 shadow-xs overflow-hidden"
              >
                {/* Review Header card info */}
                <div className="bg-gray-50 border-b border-gray-150 px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider block mb-1">
                      Product Name
                    </span>
                    <Link
                      to={`/product/${review.product_id}`}
                      className="text-indigo-600 font-bold text-sm hover:underline"
                    >
                      {productsMap[review.product_id] || `Product ID #${review.product_id}`}
                    </Link>
                  </div>
                  <div className="text-right sm:text-right">
                    <span className="text-xs text-gray-400 block mb-1">Date Submitted</span>
                    <span className="text-xs font-semibold text-gray-600">
                      {new Date(review.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Card Body */}
                <div className="p-6 flex flex-col md:flex-row gap-6">
                  {/* Left review metadata / comment */}
                  <div className="flex-1">
                    <div className="flex items-center gap-4 mb-4">
                      <div>
                        <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider block mb-1">
                          Author
                        </span>
                        <span className="text-sm font-bold text-gray-700 bg-gray-100 px-2 py-0.5 rounded-sm">
                          {review.user_id}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider block mb-1">
                          Rating
                        </span>
                        {renderStars(review.rating)}
                      </div>
                    </div>

                    <div>
                      <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider block mb-1">
                        Comment
                      </span>
                      <p className="text-gray-700 text-sm leading-relaxed bg-gray-50 rounded-lg p-4 border border-gray-100">
                        {review.comment}
                      </p>
                    </div>
                  </div>

                  {/* Attached Image preview */}
                  {review.image_data && (
                    <div className="flex-shrink-0">
                      <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider block mb-2">
                        Attached Image
                      </span>
                      <div className="w-32 h-32 md:w-40 md:h-40 bg-gray-50 rounded-lg overflow-hidden border border-gray-150 shadow-2xs">
                        <img
                          src={review.image_data}
                          alt="Review attachment pending moderation"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    </div>
                  )}

                  {/* Moderation Controls */}
                  <div className="flex md:flex-col justify-end md:justify-center gap-3 border-t md:border-t-0 md:border-l border-gray-100 pt-4 md:pt-0 md:pl-6 flex-shrink-0">
                    <button
                      onClick={() => handleAction(review.id, 'approve')}
                      disabled={actioningId !== null}
                      className="inline-flex items-center gap-1.5 bg-green-600 text-white font-semibold text-sm px-4 py-2.5 rounded-md hover:bg-green-700 transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                    >
                      {actioningId === review.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Check className="h-4 w-4" />
                      )}
                      <span>Approve</span>
                    </button>
                    <button
                      onClick={() => handleAction(review.id, 'reject')}
                      disabled={actioningId !== null}
                      className="inline-flex items-center gap-1.5 bg-red-600 text-white font-semibold text-sm px-4 py-2.5 rounded-md hover:bg-red-700 transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                    >
                      {actioningId === review.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <X className="h-4 w-4" />
                      )}
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
};
