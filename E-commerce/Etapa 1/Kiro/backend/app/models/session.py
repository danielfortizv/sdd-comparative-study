"""Session representation (backend-established, reflected on the frontend).

A ``Session`` indicates that a Customer is signed in. It drives the visible
active/inactive session indicator and the checkout identification gate
(Requirements 6.4, 6.5, 6.9). It holds no password or credential value
(Requirement 7.3).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Session(BaseModel):
    """The state indicating that a Customer is signed in.

    Attributes:
        active: Whether a Session is currently active.
        customer_id: The identified Customer (serialized as ``customerId``);
            ``None`` when no Session is active.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    active: bool = False
    customer_id: str | None = None
