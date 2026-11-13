// Property-based and example tests for the pure review helpers (Stage 2).
//
// The authoritative tagged test for Property 4 (visitors cannot submit
// reviews) lives here because submission gating is a frontend concern. The
// rating-summary example test references Property 9 without re-tagging it (the
// authoritative Property 9 tagged test is on the backend).

import { describe, expect, it } from "vitest";
import fc from "fast-check";

import type { Review, SessionState } from "../types";
import { canSubmitReview, computeRatingSummary } from "./reviews";

describe("Property 4: Visitors cannot submit reviews", () => {
  // Feature: ecommerce-stage2, Property 4: Visitors cannot submit reviews
  // Validates: Requirements 1.2
  it("submission is permitted only for an active, non-moderator customer session", () => {
    fc.assert(
      fc.property(
        fc.record({
          active: fc.boolean(),
          identity: fc.option(fc.string({ minLength: 1, maxLength: 12 }), {
            nil: null,
          }),
          isModerator: fc.boolean(),
        }),
        (session: SessionState) => {
          const allowed = canSubmitReview(session);
          const expected =
            session.active === true &&
            session.identity !== null &&
            session.isModerator !== true;
          expect(allowed).toBe(expected);
          // A visitor (no active session) can never submit.
          if (!session.active) {
            expect(allowed).toBe(false);
          }
        },
      ),
    );
  });
});

describe("Rating summary (references Property 9)", () => {
  // References design Property 9 (authoritative tagged test on the backend):
  // the summary counts and averages approved reviews only.
  function review(rating: number, state: Review["moderationState"]): Review {
    return {
      id: `r-${Math.random()}`,
      productId: "p-001",
      authorIdentity: "a",
      rating,
      title: null,
      text: "t",
      images: [],
      moderationState: state,
    };
  }

  it("counts and averages approved reviews only", () => {
    const reviews = [
      review(5, "approved"),
      review(3, "approved"),
      review(1, "pending"),
      review(1, "rejected"),
    ];
    expect(computeRatingSummary(reviews)).toEqual({ count: 2, average: 4 });
  });

  it("returns zero for no approved reviews", () => {
    expect(computeRatingSummary([review(2, "pending")])).toEqual({
      count: 0,
      average: 0,
    });
    expect(computeRatingSummary([])).toEqual({ count: 0, average: 0 });
  });
});
