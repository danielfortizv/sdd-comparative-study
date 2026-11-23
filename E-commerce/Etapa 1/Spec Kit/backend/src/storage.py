import json
import os
from typing import Dict, List, Optional

# In-memory storage structures
# Users store: {identifier: hashed_password}
USERS_DB: Dict[str, str] = {}

# Sessions store: {session_token: identifier}
SESSIONS_DB: Dict[str, str] = {}

# Catalog products cache
PRODUCTS_LIST: List[dict] = []


def load_catalog_products() -> List[dict]:
    """Loads products from backend/src/data/catalog.json into PRODUCTS_LIST if not loaded."""
    global PRODUCTS_LIST
    if PRODUCTS_LIST:
        return PRODUCTS_LIST

    current_dir = os.path.dirname(os.path.abspath(__file__))
    catalog_path = os.path.join(current_dir, "data", "catalog.json")

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            PRODUCTS_LIST = json.load(f)
    except Exception as e:
        # Fallback or empty if catalog cannot be loaded
        print(f"Error loading catalog products: {e}")
        PRODUCTS_LIST = []

    return PRODUCTS_LIST


def clear_storage() -> None:
    """Utility function to reset in-memory data (primarily for testing)."""
    global USERS_DB, SESSIONS_DB, PRODUCTS_LIST
    USERS_DB.clear()
    SESSIONS_DB.clear()
    PRODUCTS_LIST.clear()
