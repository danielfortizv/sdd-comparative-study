"""Customer data model (backend-owned).

A ``Customer`` represents an account used to identify a person during the
journey. It collects only the minimum credential contract: an ``identifier``
and a password. The password is accepted only as request input elsewhere; it
is stored here solely as ``passwordHash`` and is never kept or returned as
readable plain text (Requirements 5.1, 7.3).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Customer(BaseModel):
    """An account used to identify a Customer.

    Attributes:
        id: Account identity.
        identifier: The credential identifier used to identify a Customer.
        password_hash: Hashed credential (serialized as ``passwordHash``);
            never the readable plain-text password.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    identifier: str
    password_hash: str
