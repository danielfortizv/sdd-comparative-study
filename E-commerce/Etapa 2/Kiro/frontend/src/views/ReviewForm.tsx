// Review submission form (Stage 2, design: Frontend Components — ReviewForm).
//
// Shown only to an active non-moderator customer; otherwise an identification
// prompt is shown and submission is blocked (R1.1, R1.2). Collects a rating
// (1-5), an optional title, a required text body, and up to 3 image
// attachments (R1.3-R1.5, R2.1). Client-side validation mirrors the backend
// and surfaces field-level errors (R7.2). On success it shows the
// "submitted, awaiting moderation" confirmation (R1.9) and surfaces duplicate
// and validation errors from the backend. A loading indicator is shown while
// the request is in flight (R7.1). All controls are labeled (R8.2, R8.3).

import { useState, type FormEvent } from "react";

import { ApiError, apiClient } from "../api/client";
import { useJourney } from "../state/JourneyState";
import {
  MAX_IMAGES,
  canSubmitReview,
  readImageAsInput,
  validateSubmission,
} from "../state/reviews";
import type { ReviewImageInput } from "../types";

const RATING_OPTIONS = [1, 2, 3, 4, 5] as const;

/** Map a backend offending-field list to a readable message (no values). */
function describeOffending(fields: string[]): string {
  const labels: Record<string, string> = {
    rating: "rating",
    text: "review text",
    title: "title",
    images: "images",
  };
  const names = fields.map((f) => labels[f] ?? f).join(", ");
  return `Please correct the following field(s): ${names}.`;
}

export function ReviewForm({
  productId,
  onSubmitted,
}: {
  productId: string;
  onSubmitted?: () => void;
}) {
  const { session } = useJourney();
  const allowed = canSubmitReview(session);

  const [rating, setRating] = useState<number>(5);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [images, setImages] = useState<ReviewImageInput[]>([]);
  const [imageSizes, setImageSizes] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);

  if (!allowed) {
    // Identification gate (R1.2): visitors and moderators cannot author reviews.
    return (
      <div data-testid="review-form-gate">
        <p>
          <a href="#account">Sign in as a customer</a> to write a review for
          this product.
        </p>
      </div>
    );
  }

  async function handleFiles(fileList: FileList | null) {
    if (fileList === null) {
      return;
    }
    const files = Array.from(fileList).slice(0, MAX_IMAGES);
    try {
      const inputs = await Promise.all(files.map(readImageAsInput));
      setImages(inputs);
      setImageSizes(files.map((file) => file.size));
    } catch {
      setError("An attached image could not be read. Please try another file.");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const offending = validateSubmission({
      rating,
      text,
      title: title === "" ? null : title,
      images: images.map((img, index) => ({
        mediaType: img.mediaType,
        sizeBytes: imageSizes[index] ?? 0,
      })),
    });
    if (offending.length > 0) {
      setError(describeOffending(offending));
      return;
    }

    setPending(true);
    try {
      await apiClient.submitReview(productId, {
        rating,
        text,
        title: title === "" ? null : title,
        images,
      });
      setConfirmation(
        "Your review was submitted and is awaiting moderation.",
      );
      setTitle("");
      setText("");
      setImages([]);
      setImageSizes([]);
      onSubmitted?.();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError(
            err.detail?.message ??
              "You have already reviewed this product. Only one review per product is allowed.",
          );
        } else if (err.detail?.offendingFields?.length) {
          setError(describeOffending(err.detail.offendingFields));
        } else {
          setError(
            err.detail?.message ??
              "The review could not be submitted. Please try again.",
          );
        }
      } else {
        setError("The review could not be submitted. Please try again.");
      }
    } finally {
      setPending(false);
    }
  }

  if (confirmation !== null) {
    return (
      <div role="status" aria-live="polite" data-testid="review-submitted">
        <p>{confirmation}</p>
        <button
          type="button"
          onClick={() => setConfirmation(null)}
          data-testid="write-another-review"
        >
          Write another review
        </button>
      </div>
    );
  }

  return (
    <form
      aria-labelledby={`review-form-heading-${productId}`}
      onSubmit={handleSubmit}
      data-testid="review-form"
    >
      <h4 id={`review-form-heading-${productId}`}>Write a review</h4>

      <div>
        <label htmlFor={`review-rating-${productId}`}>Rating (1 to 5)</label>
        <select
          id={`review-rating-${productId}`}
          value={rating}
          onChange={(event) => setRating(Number(event.target.value))}
        >
          {RATING_OPTIONS.map((value) => (
            <option key={value} value={value}>
              {value} star{value === 1 ? "" : "s"}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor={`review-title-${productId}`}>Title (optional)</label>
        <input
          id={`review-title-${productId}`}
          type="text"
          value={title}
          maxLength={200}
          onChange={(event) => setTitle(event.target.value)}
        />
      </div>

      <div>
        <label htmlFor={`review-text-${productId}`}>Your review</label>
        <textarea
          id={`review-text-${productId}`}
          value={text}
          onChange={(event) => setText(event.target.value)}
          aria-describedby={error !== null ? `review-error-${productId}` : undefined}
        />
      </div>

      <div>
        <label htmlFor={`review-images-${productId}`}>
          Attach images (up to {MAX_IMAGES}, optional)
        </label>
        <input
          id={`review-images-${productId}`}
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          multiple
          onChange={(event) => void handleFiles(event.target.files)}
        />
        {images.length > 0 && (
          <p data-testid="review-image-count">
            {images.length} image{images.length === 1 ? "" : "s"} attached.
          </p>
        )}
      </div>

      {error !== null && (
        <p
          id={`review-error-${productId}`}
          role="alert"
          aria-live="assertive"
          data-testid="review-error"
        >
          {error}
        </p>
      )}

      <button type="submit" disabled={pending} data-testid="submit-review">
        {pending ? "Submitting review…" : "Submit review"}
      </button>

      {pending && (
        <p role="status" aria-live="polite" data-testid="review-loading">
          Submitting your review… Please wait.
        </p>
      )}
    </form>
  );
}
