from datetime import datetime, timezone
import sqlite3
from fastapi import status
from src.services.commerce.main import response_cache, DB_PATH


def test_cache_set_get_and_invalidate():
    response_cache.clear()
    
    # Verify cache miss
    assert response_cache.get("test_key") is None
    
    # Verify cache set
    response_cache.set("test_key", {"data": "hello"}, ttl_seconds=5)
    assert response_cache.get("test_key") == {"data": "hello"}
    
    # Verify manual invalidation
    response_cache.invalidate("test_key")
    assert response_cache.get("test_key") is None


def test_catalog_response_caching(client_commerce):
    response_cache.clear()
    
    # Make first request to cache products catalog
    resp1 = client_commerce.get("/api/products")
    assert resp1.status_code == status.HTTP_200_OK
    
    # Modify products directly in DB to see if cache returns old data (proving caching works!)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE products SET name = 'MOCK_KEYBOARD' WHERE product_id = 'prod_004'")
        conn.commit()
        
    # Second request should get cached results (the original name, not MOCK_KEYBOARD!)
    resp2 = client_commerce.get("/api/products")
    assert resp2.status_code == status.HTTP_200_OK
    keyboard_product2 = next(p for p in resp2.json() if p["product_id"] == "prod_004")
    assert keyboard_product2["name"] != "MOCK_KEYBOARD"
    
    # Clear cache and verify we get fresh DB values
    response_cache.clear()
    resp3 = client_commerce.get("/api/products")
    assert resp3.status_code == status.HTTP_200_OK
    keyboard_product3 = next(p for p in resp3.json() if p["product_id"] == "prod_004")
    assert keyboard_product3["name"] == "MOCK_KEYBOARD"


def test_reviews_selective_cache_invalidation():
    response_cache.clear()
    
    # Populate cache for keyboard reviews
    reviews_key = "reviews_prod_004"
    response_cache.set(reviews_key, [{"review_id": "r-1", "comment": "Good"}], ttl_seconds=60)
    
    # Invalidate other product reviews (should NOT affect keyboard reviews)
    response_cache.invalidate("reviews_prod_001")
    assert response_cache.get(reviews_key) == [{"review_id": "r-1", "comment": "Good"}]
    
    # Invalidate keyboard reviews
    response_cache.invalidate(reviews_key)
    assert response_cache.get(reviews_key) is None
