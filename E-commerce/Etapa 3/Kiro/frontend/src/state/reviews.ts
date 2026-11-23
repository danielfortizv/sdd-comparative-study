// Pure, testable review helpers (Stage 2). These mirror the backend rules so
// the frontend can validate before calling and compute display aggregates
// without the DOM. All text is in English (Requirement 9.7).

import type { Review, ReviewImageInput, SessionState } from "../types";

// Field bounds mirroring the backend (Assumptions A2, A3).
export const MIN_RATING = 1;
export const MAX_RATING = 5;
export const MAX_TEXT_LENGTH = 2000;
export const MAX_TITLE_LENGTH = 120;
export const MAX_IMAGES = 3;
export const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
export const ALLOWED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
] as const;

/**
 * Whether the given session may submit a review: an active, non-moderator
 * customer session (Requirement 1.2, Assumption A1, A5). Visitors (no active
 * session) and moderators cannot author reviews.
 *
 * This is the authoritative frontend gating logic exercised by the Property 4
 * test.
 */
export function canSubmitReview(session: SessionState): boolean {
  return (
    session.active === true &&
    session.identity !== null &&
    session.isModerator !== true
  );
}

/**
 * Compute the rating summary (count and average) from a list of reviews,
 * counting approved reviews only (Requirements 4.3, 4.5). The average is
 * rounded to two decimals; an empty approved set yields an average of 0.
 */
export function computeRatingSummary(reviews: Review[]): {
  count: number;
  average: number;
} {
  const approved = reviews.filter((r) => r.moderationState === "approved");
  const count = approved.length;
  if (count === 0) {
    return { count: 0, average: 0 };
  }
  const sum = approved.reduce((acc, r) => acc + r.rating, 0);
  return { count, average: Math.round((sum / count) * 100) / 100 };
}

/** The offending fields in a would-be submission, mirroring the backend. */
export function validateSubmission(input: {
  rating: number | null;
  text: string;
  title?: string | null;
  images: { mediaType: string; sizeBytes: number }[];
}): string[] {
  const offending: string[] = [];

  if (
    input.rating === null ||
    !Number.isInteger(input.rating) ||
    input.rating < MIN_RATING ||
    input.rating > MAX_RATING
  ) {
    offending.push("rating");
  }
  if (input.text.trim() === "" || input.text.length > MAX_TEXT_LENGTH) {
    offending.push("text");
  }
  if (
    input.title != null &&
    input.title.length > MAX_TITLE_LENGTH
  ) {
    offending.push("title");
  }
  if (input.images.length > MAX_IMAGES) {
    offending.push("images");
  } else if (
    input.images.some(
      (img) =>
        !ALLOWED_IMAGE_TYPES.includes(
          img.mediaType as (typeof ALLOWED_IMAGE_TYPES)[number],
        ) || img.sizeBytes > MAX_IMAGE_BYTES,
    )
  ) {
    offending.push("images");
  }

  return offending;
}

/**
 * Read a File into a {@link ReviewImageInput} (base64 payload + media type),
 * matching the backend's base64-in-JSON transfer (Assumption A3). Returns a
 * promise so callers can await the encoded result.
 */
export function readImageAsInput(file: File): Promise<ReviewImageInput> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("The image could not be read."));
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("The image could not be read."));
        return;
      }
      // Data URL shape: "data:<mediaType>;base64,<data>"; take the payload.
      const commaIndex = result.indexOf(",");
      const dataBase64 = commaIndex >= 0 ? result.slice(commaIndex + 1) : result;
      resolve({ mediaType: file.type, dataBase64 });
    };
    reader.readAsDataURL(file);
  });
}
