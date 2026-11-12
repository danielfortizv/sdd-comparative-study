"""Backend application package for the Stage 1 e-commerce demonstration.

The package is organized into three layers so presentation, business logic,
and data access are not mixed (Requirement 14.4):

- ``api``: FastAPI routers (presentation / request-response handling).
- ``services``: business logic (catalog retrieval, authentication, checkout).
- ``data``: in-process demonstration data store (data-access layer).
"""
