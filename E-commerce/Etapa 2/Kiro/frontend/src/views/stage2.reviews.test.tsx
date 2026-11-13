// Focused Stage 2 component tests: review form gating, product reviews
// display, and moderation view gating/decisions. These exercise the key
// requirements concisely (R1.2, R3.6, R4.1, R4.3, R4.4, R6.2, R8.4) with the
// api client mocked.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect, type ReactNode } from "react";

import type { ProductReviews as ProductReviewsData, Review } from "../types";
import { JourneyProvider, useJourney } from "../state/JourneyState";
import { ProductReviews } from "./ProductReviews";
import { ModerationView } from "./ModerationView";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>(
    "../api/client",
  );
  return {
    ...actual,
    apiClient: {
      listProductReviews: vi.fn(),
      submitReview: vi.fn(),
      reviewImageUrl: (u: string) => `http://localhost:8000${u}`,
      listModerationQueue: vi.fn(),
      approveReview: vi.fn(),
      rejectReview: vi.fn(),
    },
  };
});

import { apiClient } from "../api/client";

const listProductReviews = apiClient.listProductReviews as unknown as ReturnType<typeof vi.fn>;
const listModerationQueue = apiClient.listModerationQueue as unknown as ReturnType<typeof vi.fn>;
const approveReview = apiClient.approveReview as unknown as ReturnType<typeof vi.fn>;

function review(overrides: Partial<Review> = {}): Review {
  return {
    id: "r-1",
    productId: "p-001",
    authorIdentity: "shopper",
    rating: 5,
    title: "Great",
    text: "Loved it",
    images: [],
    moderationState: "approved",
    ...overrides,
  };
}

function Session({
  active,
  identity,
  isModerator,
  children,
}: {
  active: boolean;
  identity: string | null;
  isModerator?: boolean;
  children: ReactNode;
}) {
  const { signInSession } = useJourney();
  useEffect(() => {
    if (active && identity) {
      signInSession(identity, isModerator === true);
    }
  }, [active, identity, isModerator, signInSession]);
  return <>{children}</>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("ProductReviews display", () => {
  it("shows approved reviews, the rating summary, and image alt text (R4.1, R4.3, R8.4)", async () => {
    const data: ProductReviewsData = {
      reviews: [
        review({
          id: "r-1",
          rating: 4,
          images: [{ id: "img-1", imageUrl: "/reviews/images/img-1", mediaType: "image/png" }],
        }),
      ],
      summary: { count: 1, average: 4 },
      ownReview: null,
    };
    listProductReviews.mockResolvedValue(data);

    render(
      <JourneyProvider>
        <ProductReviews productId="p-001" />
      </JourneyProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("rating-summary")).toBeInTheDocument());
    expect(screen.getByTestId("rating-summary")).toHaveTextContent(/4 average from 1 review/i);
    const image = screen.getByTestId("review-image");
    expect(image).toHaveAttribute("alt", expect.stringMatching(/image 1/i));
  });

  it("renders review text as text so stored markup is inert (R6.2)", async () => {
    listProductReviews.mockResolvedValue({
      reviews: [review({ text: "<script>alert(1)</script>" })],
      summary: { count: 1, average: 5 },
      ownReview: null,
    });
    render(
      <JourneyProvider>
        <ProductReviews productId="p-001" />
      </JourneyProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("review-text")).toBeInTheDocument());
    // The literal markup is present as text, not as a <script> element.
    expect(screen.getByTestId("review-text")).toHaveTextContent("<script>alert(1)</script>");
    expect(document.querySelector("script")).toBeNull();
  });

  it("shows a no-reviews empty state when there are no approved reviews (R4.4)", async () => {
    listProductReviews.mockResolvedValue({
      reviews: [],
      summary: { count: 0, average: 0 },
      ownReview: null,
    });
    render(
      <JourneyProvider>
        <ProductReviews productId="p-001" />
      </JourneyProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("reviews-empty-state")).toBeInTheDocument());
  });

  it("gates the review form to signed-in customers (R1.2)", async () => {
    listProductReviews.mockResolvedValue({ reviews: [], summary: { count: 0, average: 0 }, ownReview: null });
    render(
      <JourneyProvider>
        <ProductReviews productId="p-001" />
      </JourneyProvider>,
    );
    // Visitor: the form is replaced by an identification gate.
    await waitFor(() => expect(screen.getByTestId("review-form-gate")).toBeInTheDocument());
    expect(screen.queryByTestId("review-form")).not.toBeInTheDocument();
  });

  it("shows the review form to an active customer (R1.1)", async () => {
    listProductReviews.mockResolvedValue({ reviews: [], summary: { count: 0, average: 0 }, ownReview: null });
    render(
      <JourneyProvider>
        <Session active identity="shopper">
          <ProductReviews productId="p-001" />
        </Session>
      </JourneyProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("review-form")).toBeInTheDocument());
    expect(screen.getByTestId("submit-review")).toBeInTheDocument();
  });
});

describe("ModerationView gating and decisions", () => {
  it("requires a moderator session (R3.6)", () => {
    render(
      <JourneyProvider>
        <Session active identity="shopper">
          <ModerationView />
        </Session>
      </JourneyProvider>,
    );
    expect(screen.getByTestId("moderation-access-required")).toBeInTheDocument();
    expect(listModerationQueue).not.toHaveBeenCalled();
  });

  it("shows the queue and approves an item, removing it from the queue (R3.1, R3.3, R3.5, R3.8)", async () => {
    listModerationQueue.mockResolvedValue([review({ id: "r-9", moderationState: "pending" })]);
    approveReview.mockResolvedValue(review({ id: "r-9", moderationState: "approved" }));

    render(
      <JourneyProvider>
        <Session active identity="moderator" isModerator>
          <ModerationView />
        </Session>
      </JourneyProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("moderation-item-r-9")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("approve-r-9"));
    await waitFor(() =>
      expect(screen.getByTestId("moderation-confirmation")).toHaveTextContent(/approved/i),
    );
    expect(screen.queryByTestId("moderation-item-r-9")).not.toBeInTheDocument();
  });

  it("shows an empty-queue state (R7.4)", async () => {
    listModerationQueue.mockResolvedValue([]);
    render(
      <JourneyProvider>
        <Session active identity="moderator" isModerator>
          <ModerationView />
        </Session>
      </JourneyProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("moderation-empty-state")).toBeInTheDocument());
  });
});
