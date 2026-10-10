"""Data-access layer: in-process demonstration data store.

This layer holds fixed in-memory catalog product data and in-process account
storage for the running service. It stores no order records (checkout
confirmation is non-persistent). It is the only layer that touches the store;
callers always go through the service layer.
"""

from app.data.accounts import AccountStore, account_store
from app.data.catalog import get_product, list_products

__all__ = [
    "AccountStore",
    "account_store",
    "get_product",
    "list_products",
]
