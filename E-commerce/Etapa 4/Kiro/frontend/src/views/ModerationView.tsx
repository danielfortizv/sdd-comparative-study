// Moderation view (Stage 2, design: Frontend Components — ModerationView).
//
// Shown only to an active moderator session; otherwise a moderator-access
// prompt is shown (R3.6). Loads the pending moderation queue (R3.1), displays
// each pending review's product, rating, text, images, and author (R3.2), and
// provides Approve and Reject controls (R3.3, R3.4) with a visible decision
// confirmation (R3.8). Decided reviews leave the queue (R3.5). Shows an
// empty-queue state (R7.4) and loading/error states (R7.1, R7.3).

import { useCallback, useEffect, useState } from "react";

import { ApiError, apiClient } from "../api/client";
import { useJourney } from "../state/JourneyState";
import type { Review } from "../types";

export function ModerationView() {
  const { session } = useJourney();
  const isModerator = session.active && session.isModerator === true;

  const [queue, setQueue] = useState<Review[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setQueue(await apiClient.listModerationQueue());
    } catch {
      setError("The moderation queue could not be loaded. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isModerator) {
      void load();
    }
  }, [isModerator, load]);

  async function decide(review: Review, decision: "approve" | "reject") {
    setError(null);
    try {
      if (decision === "approve") {
        await apiClient.approveReview(review.id);
      } else {
        await apiClient.rejectReview(review.id);
      }
      setConfirmation(
        `Review ${decision === "approve" ? "approved" : "rejected"}.`,
      );
      // The decided review leaves the queue (R3.5).
      setQueue((current) => current.filter((item) => item.id !== review.id));
    } catch (err) {
      const message =
        err instanceof ApiError && err.detail?.message
          ? err.detail.message
          : "The decision could not be applied. Please try again.";
      setError(message);
    }
  }

  if (!isModerator) {
    return (
      <section aria-labelledby="moderation-heading">
        <h2 id="moderation-heading">Moderation</h2>
        <p data-testid="moderation-access-required">
          Moderator access is required. Sign in with a moderator account to
          review pending submissions.
        </p>
      </section>
    );
  }

  return (
    <section aria-labelledby="moderation-heading">
      <h2 id="moderation-heading">Moderation</h2>

      <p role="status" aria-live="polite" data-testid="moderation-confirmation">
        {confirmation}
      </p>

      {loading && (
        <p role="status" data-testid="moderation-loading">
          Loading the moderation queue…
        </p>
      )}

      {!loading && error && (
        <p role="alert" data-testid="moderation-error">
          {error}
        </p>
      )}

      {!loading && !error && queue.length === 0 && (
        <p data-testid="moderation-empty-state">
          There is nothing to moderate right now.
        </p>
      )}

      {!loading && !error && queue.length > 0 && (
        <ul className="moderation-queue" aria-label="Pending reviews">
          {queue.map((review) => (
            <li key={review.id} data-testid={`moderation-item-${review.id}`}>
              <p data-testid="moderation-product">Product: {review.productId}</p>
              <p data-testid="moderation-rating">Rating: {review.rating} / 5</p>
              {review.title && <p>Title: {review.title}</p>}
              <p data-testid="moderation-text">{review.text}</p>
              <p data-testid="moderation-author">By {review.authorIdentity}</p>
              {review.images.length > 0 && (
                <ul aria-label="Attached images for review">
                  {review.images.map((image, index) => (
                    <li key={image.id}>
                      <img
                        src={apiClient.reviewImageUrl(image.imageUrl)}
                        alt={`Pending review image ${index + 1} by ${review.authorIdentity}`}
                      />
                    </li>
                  ))}
                </ul>
              )}
              <button
                type="button"
                onClick={() => void decide(review, "approve")}
                data-testid={`approve-${review.id}`}
              >
                Approve
              </button>
              <button
                type="button"
                onClick={() => void decide(review, "reject")}
                data-testid={`reject-${review.id}`}
              >
                Reject
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
