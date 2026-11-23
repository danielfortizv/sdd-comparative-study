"""Focused Stage 2 tests: reviews with images and moderation.

Covers the review/moderation service logic, the correctness properties whose
authoritative tagged test lives on the backend (Properties 1, 2, 3, 5, 6, 7,
8, 9, 10 — Property 4 is a frontend concern), and the key endpoint behaviors.
These are deliberately concise but meaningful checks of the Stage 2 design.

A tiny 1x1 PNG is used as a valid demonstration image so image validation and
storage paths are exercised without any external asset.
"""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from app.data.accounts import account_store
from app.data.review_images import ImageStore, ImageValidationError
from app.data.reviews import ReviewStore
from app.main import app
from app.models.review import Review, ReviewImageInput
from app.services import review_service, signin_service
from app.services.moderator_seed import (
    MODERATOR_IDENTIFIER,
    MODERATOR_PASSWORD,
    seed_moderator,
)
from app.services.review_service import (
    DuplicateReviewError,
    ModerationError,
    ReviewValidationError,
)

# A minimal valid 1x1 transparent PNG, base64-encoded (a real, decodable image).
_PNG_1X1 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
).decode("ascii")

VALID_PRODUCT = "p-001"


def _image_input() -> ReviewImageInput:
    return ReviewImageInput(media_type="image/png", data_base64=_PNG_1X1)


def _fresh_store(tmp_path=None) -> ReviewStore:
    return ReviewStore()


def _image_store(tmp_path) -> ImageStore:
    return ImageStore(image_dir=tmp_path / "images")


# --- Service: submission validation ------------------------------------------


# Feature: ecommerce-stage2, Property 1: Review submission validation rejects
# and identifies all offending fields.
@given(
    rating=st.integers(min_value=-5, max_value=12),
    text=st.text(max_size=5),
    title_len=st.integers(min_value=0, max_value=200),
    image_count=st.integers(min_value=0, max_value=6),
)
def test_property_1_submission_validation_identifies_offending_fields(
    rating: int, text: str, title_len: int, image_count: int
) -> None:
    """The reported offending fields equal exactly the set that violate a rule."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        images_store = ImageStore(image_dir=Path(tmp))
        store = ReviewStore()
        title = "x" * title_len if title_len > 0 else None
        images = [_image_input() for _ in range(image_count)]

        expected: set[str] = set()
        if rating < 1 or rating > 5:
            expected.add("rating")
        if text.strip() == "" or len(text) > review_service.MAX_TEXT_LENGTH:
            expected.add("text")
        if title is not None and len(title) > review_service.MAX_TITLE_LENGTH:
            expected.add("title")
        if image_count > review_service.MAX_IMAGES:
            expected.add("images")

        try:
            review_service.submit_review(
                VALID_PRODUCT,
                "author-a",
                rating,
                text,
                title,
                images,
                store=store,
                images_store=images_store,
            )
            created = True
            offending: set[str] = set()
        except ReviewValidationError as error:
            created = False
            offending = set(error.offending_fields)

        if expected:
            assert created is False
            assert offending == expected
        else:
            assert created is True


# Feature: ecommerce-stage2, Property 2: Valid submission creates a pending
# review associated with product and author.
@given(
    rating=st.integers(min_value=1, max_value=5),
    text=st.text(min_size=1, max_size=100).filter(lambda t: t.strip() != ""),
)
def test_property_2_valid_submission_creates_pending_review(
    rating: int, text: str
) -> None:
    """A valid submission yields a pending review with the right product/author."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore()
        images_store = ImageStore(image_dir=Path(tmp))
        review = review_service.submit_review(
            VALID_PRODUCT,
            "author-b",
            rating,
            text,
            None,
            [],
            store=store,
            images_store=images_store,
        )
        assert review.product_id == VALID_PRODUCT
        assert review.author_identity == "author-b"
        assert review.moderation_state == "pending"
        assert review.rating == rating


# Feature: ecommerce-stage2, Property 3: One review per customer per product.
@given(rating=st.integers(min_value=1, max_value=5))
def test_property_3_one_review_per_customer_per_product(rating: int) -> None:
    """A second submission by the same author for the same product is rejected."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore()
        images_store = ImageStore(image_dir=Path(tmp))
        review_service.submit_review(
            VALID_PRODUCT, "author-c", rating, "good", None, [],
            store=store, images_store=images_store,
        )
        with pytest.raises(DuplicateReviewError):
            review_service.submit_review(
                VALID_PRODUCT, "author-c", rating, "again", None, [],
                store=store, images_store=images_store,
            )
        assert len(store.list_by_product(VALID_PRODUCT)) == 1


# Feature: ecommerce-stage2, Property 5: Approve/reject are terminal
# transitions from pending.
@given(decision=st.sampled_from(["approve", "reject"]))
def test_property_5_approve_reject_terminal_from_pending(decision: str) -> None:
    """A review can only be decided while pending; a decision cannot be redone."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore()
        images_store = ImageStore(image_dir=Path(tmp))
        review = review_service.submit_review(
            VALID_PRODUCT, "author-d", 4, "fine", None, [],
            store=store, images_store=images_store,
        )
        apply = (
            review_service.approve_review
            if decision == "approve"
            else review_service.reject_review
        )
        decided = apply(review.id, store=store)
        assert decided.moderation_state == ("approved" if decision == "approve" else "rejected")
        # A second decision (either kind) is rejected: the state is terminal.
        with pytest.raises(ModerationError):
            review_service.approve_review(review.id, store=store)
        with pytest.raises(ModerationError):
            review_service.reject_review(review.id, store=store)


# Feature: ecommerce-stage2, Property 7: Only approved reviews are publicly
# visible.
@given(states=st.lists(st.sampled_from(["pending", "approved", "rejected"]), min_size=0, max_size=8))
def test_property_7_only_approved_reviews_visible(states: list[str]) -> None:
    """The public list is exactly the approved reviews for the product."""
    store = ReviewStore()
    for i, state in enumerate(states):
        store.add(
            Review(
                id=f"r-{i}",
                product_id=VALID_PRODUCT,
                author_identity=f"a-{i}",
                rating=3,
                text="t",
                moderation_state=state,
            )
        )
    visible = review_service.list_approved_reviews(VALID_PRODUCT, store=store)
    assert all(r.moderation_state == "approved" for r in visible)
    assert len(visible) == states.count("approved")


# Feature: ecommerce-stage2, Property 8: Moderation queue contains exactly the
# pending reviews.
@given(states=st.lists(st.sampled_from(["pending", "approved", "rejected"]), min_size=0, max_size=8))
def test_property_8_queue_is_exactly_pending(states: list[str]) -> None:
    """The moderation queue equals exactly the pending reviews."""
    store = ReviewStore()
    for i, state in enumerate(states):
        store.add(
            Review(
                id=f"q-{i}",
                product_id=VALID_PRODUCT,
                author_identity=f"a-{i}",
                rating=3,
                text="t",
                moderation_state=state,
            )
        )
    queue = review_service.list_pending_reviews(store=store)
    assert all(r.moderation_state == "pending" for r in queue)
    assert len(queue) == states.count("pending")


# Feature: ecommerce-stage2, Property 9: Rating summary derives from approved
# ratings only.
@given(
    approved=st.lists(st.integers(min_value=1, max_value=5), min_size=0, max_size=8),
    other=st.lists(st.integers(min_value=1, max_value=5), min_size=0, max_size=8),
)
def test_property_9_summary_from_approved_only(
    approved: list[int], other: list[int]
) -> None:
    """Summary count/average use approved ratings only and ignore the rest."""
    store = ReviewStore()
    idx = 0
    for rating in approved:
        store.add(Review(id=f"ap-{idx}", product_id=VALID_PRODUCT, author_identity=f"x{idx}", rating=rating, text="t", moderation_state="approved"))
        idx += 1
    for rating in other:
        state = "pending" if idx % 2 == 0 else "rejected"
        store.add(Review(id=f"ot-{idx}", product_id=VALID_PRODUCT, author_identity=f"x{idx}", rating=rating, text="t", moderation_state=state))
        idx += 1

    summary = review_service.rating_summary(VALID_PRODUCT, store=store)
    assert summary.count == len(approved)
    if approved:
        assert summary.average == pytest.approx(round(sum(approved) / len(approved), 2))
    else:
        assert summary.average == 0.0


# Feature: ecommerce-stage2, Property 10: Stored image set matches accepted
# images and respects the allow-list.
@given(image_count=st.integers(min_value=0, max_value=3))
def test_property_10_stored_images_match_accepted(image_count: int) -> None:
    """Every stored image has an allowed type and the count matches the input."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore()
        images_store = ImageStore(image_dir=Path(tmp))
        images = [_image_input() for _ in range(image_count)]
        review = review_service.submit_review(
            VALID_PRODUCT, f"author-img-{image_count}", 5, "pics", None, images,
            store=store, images_store=images_store,
        )
        assert len(review.images) == image_count
        allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        assert all(img.media_type in allowed for img in review.images)


# --- Image validation units (R2.3, R2.4, R6.3) -------------------------------


def test_image_store_rejects_unsupported_type_without_storing(tmp_path) -> None:
    store = ImageStore(image_dir=tmp_path / "imgs")
    with pytest.raises(ImageValidationError) as exc:
        store.validate("image/bmp", _PNG_1X1)
    assert exc.value.code == "unsupported_image_type"
    # Nothing was written (validate never writes; store() would, but we skipped it).
    assert not any((tmp_path / "imgs").glob("*")) if (tmp_path / "imgs").exists() else True


def test_image_store_rejects_oversized_without_storing(tmp_path) -> None:
    store = ImageStore(image_dir=tmp_path / "imgs")
    oversized = base64.b64encode(b"\x00" * (2 * 1024 * 1024 + 1)).decode("ascii")
    with pytest.raises(ImageValidationError) as exc:
        store.validate("image/png", oversized)
    assert exc.value.code == "image_too_large"


# --- Endpoint-level checks ----------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset shared in-process state between endpoint tests."""
    from app.data.reviews import review_store

    signin_service.reset_session()
    review_store.clear()
    seed_moderator()
    yield
    signin_service.reset_session()
    review_store.clear()


def _register_and_login(client: TestClient, identifier: str, password: str = "pw-123") -> None:
    client.post("/auth/register", json={"identifier": identifier, "password": password})
    resp = client.post("/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200


def test_submit_requires_authentication(client: TestClient) -> None:
    """Property 4 counterpart on the backend guard: visitor submission is denied."""
    signin_service.reset_session()
    resp = client.post(
        f"/products/{VALID_PRODUCT}/reviews",
        json={"rating": 5, "text": "great", "images": []},
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "authentication_required"


def test_full_moderation_workflow(client: TestClient) -> None:
    """Submit -> pending/hidden -> moderator approves -> visible + summary."""
    _register_and_login(client, "shopper-1")
    submit = client.post(
        f"/products/{VALID_PRODUCT}/reviews",
        json={"rating": 4, "text": "Solid product", "title": "Nice", "images": [{"mediaType": "image/png", "dataBase64": _PNG_1X1}]},
    )
    assert submit.status_code == 201
    review_id = submit.json()["id"]
    assert submit.json()["moderationState"] == "pending"

    # Not publicly visible while pending.
    public = client.get(f"/products/{VALID_PRODUCT}/reviews").json()
    assert public["reviews"] == []
    assert public["summary"]["count"] == 0

    # Moderator signs in and approves.
    signin_service.reset_session()
    login = client.post("/auth/login", json={"identifier": MODERATOR_IDENTIFIER, "password": MODERATOR_PASSWORD})
    assert login.status_code == 200 and login.json()["isModerator"] is True
    queue = client.get("/moderation/reviews")
    assert queue.status_code == 200 and len(queue.json()) == 1
    approve = client.post(f"/moderation/reviews/{review_id}/approve")
    assert approve.status_code == 200 and approve.json()["moderationState"] == "approved"

    # Now visible with a summary and a served image.
    public2 = client.get(f"/products/{VALID_PRODUCT}/reviews").json()
    assert public2["summary"]["count"] == 1 and public2["summary"]["average"] == 4.0
    assert len(public2["reviews"]) == 1
    image_url = public2["reviews"][0]["images"][0]["imageUrl"]
    img = client.get(image_url)
    assert img.status_code == 200 and img.headers["content-type"].startswith("image/")


def test_moderation_requires_moderator_session(client: TestClient) -> None:
    """Feature: ecommerce-stage2, Property 6 (endpoint): non-moderator is denied."""
    _register_and_login(client, "shopper-2")  # a regular customer session
    assert client.get("/moderation/reviews").status_code == 403
    # No active session at all is also denied.
    signin_service.reset_session()
    assert client.get("/moderation/reviews").status_code == 403


def test_rejected_review_stays_hidden(client: TestClient) -> None:
    _register_and_login(client, "shopper-3")
    review_id = client.post(
        f"/products/{VALID_PRODUCT}/reviews",
        json={"rating": 1, "text": "bad", "images": []},
    ).json()["id"]
    signin_service.reset_session()
    client.post("/auth/login", json={"identifier": MODERATOR_IDENTIFIER, "password": MODERATOR_PASSWORD})
    assert client.post(f"/moderation/reviews/{review_id}/reject").status_code == 200
    public = client.get(f"/products/{VALID_PRODUCT}/reviews").json()
    assert public["reviews"] == [] and public["summary"]["count"] == 0


def test_review_text_markup_returned_verbatim(client: TestClient) -> None:
    """Stored markup is returned as data (rendered as text by the frontend, R6.2)."""
    _register_and_login(client, "shopper-4")
    payload = "<script>alert('x')</script>"
    resp = client.post(
        f"/products/{VALID_PRODUCT}/reviews",
        json={"rating": 3, "text": payload, "images": []},
    )
    assert resp.status_code == 201
    assert resp.json()["text"] == payload
