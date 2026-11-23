"""Demonstration moderator seeding (service layer, Stage 2).

The moderation workflow requires a moderator account (Assumption A5). To make
the workflow demonstrable immediately, a single built-in demonstration
moderator is seeded into the shared account store at startup. The credentials
are fixed constants documented in the project README so a reviewer can sign in
as the moderator without any extra setup.

Seeding is idempotent: calling it when the moderator already exists does
nothing. The password is stored only as a one-way hash, reusing the Stage 1
password-hashing policy; the plain-text demo password is a documented
convenience for the local demo and is never stored or returned.
"""

from __future__ import annotations

import uuid

from app.data.accounts import AccountStore, account_store
from app.models.customer import Customer
from app.services.password import hash_password

# Fixed demonstration moderator credentials. Documented in the README so the
# moderation workflow can be exercised immediately. These are intentionally
# simple because this is a local, non-production demonstration.
MODERATOR_IDENTIFIER = "moderator"
MODERATOR_PASSWORD = "moderator123"


def seed_moderator(store: AccountStore | None = None) -> Customer:
    """Ensure the demonstration moderator account exists.

    Idempotent: if an account already exists for the moderator identifier it is
    returned unchanged; otherwise a new moderator ``Customer`` is created with
    ``is_moderator=True`` and a hashed password.

    Args:
        store: Account store to seed into; defaults to the shared in-process
            ``account_store``.

    Returns:
        The seeded (or pre-existing) moderator ``Customer``.
    """
    active_store = store if store is not None else account_store

    existing = active_store.get_by_identifier(MODERATOR_IDENTIFIER)
    if existing is not None:
        return existing

    # The AccountStore.create_account helper does not set is_moderator, so build
    # the moderator Customer directly and register it through the store's
    # internal mapping via create then rely on a moderator-aware create path.
    moderator = Customer(
        id=str(uuid.uuid4()),
        identifier=MODERATOR_IDENTIFIER,
        password_hash=hash_password(MODERATOR_PASSWORD),
        is_moderator=True,
    )
    active_store.add_customer(moderator)
    return moderator.model_copy()
