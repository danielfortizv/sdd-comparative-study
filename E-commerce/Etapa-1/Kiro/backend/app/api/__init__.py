"""API layer: FastAPI routers that handle HTTP requests and responses.

This layer validates request shape, delegates to the service layer, and
returns JSON responses with appropriate status codes. It contains no
business logic and never reaches the data store directly.
"""
