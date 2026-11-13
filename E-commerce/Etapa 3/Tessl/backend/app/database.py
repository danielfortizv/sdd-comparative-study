# Mock Database for Stage 1 E-Commerce

# Product data containing: id, name, image_url, description, price, availability
PRODUCTS = [
    {
        "id": 1,
        "name": "Premium Ergonomic Keyboard",
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
        "description": "Tactile mechanical switches with an ergonomic split layout for comfortable typing.",
        "price": 129.99,
        "availability": True
    },
    {
        "id": 2,
        "name": "Wireless Optical Mouse",
        "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=600&q=80",
        "description": "High-precision optical tracking with an ultra-long battery life and comfortable grip.",
        "price": 49.99,
        "availability": True
    },
    {
        "id": 3,
        "name": "Noise-Cancelling Headphones",
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
        "description": "Active noise cancellation with rich studio sound and soft ear cushions for long listening sessions.",
        "price": 199.99,
        "availability": True
    },
    {
        "id": 4,
        "name": "Stainless Steel Water Bottle",
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=600&q=80",
        "description": "Double-wall vacuum insulation keeps your beverages cold for 24 hours or hot for 12 hours.",
        "price": 24.99,
        "availability": True
    },
    {
        "id": 5,
        "name": "Travel Canvas Backpack",
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80",
        "description": "Vintage canvas backpack with spacious compartments, padded laptop sleeve, and water-resistant finish.",
        "price": 59.99,
        "availability": False  # Demonstrated out-of-stock item
    }
]

# In-memory User storage: username (string) -> dict with: username, hashed_password, salt
USERS = {}

# In-memory Session storage: token (string) -> username (string)
SESSIONS = {}

# In-memory Reviews storage: list of dicts with keys: id, product_id, rating, comment, image_base64, status, username, created_at
REVIEWS = [
    {
        "id": 1,
        "product_id": 1,
        "rating": 5,
        "comment": "Absolutely love this keyboard! The split layout takes a few days to get used to, but my wrist pain has completely disappeared. Highly recommended!",
        "image_base64": None,
        "status": "approved",
        "username": "keyboard_enthusiast",
        "created_at": "2026-11-01 10:30:00"
    },
    {
        "id": 2,
        "product_id": 1,
        "rating": 4,
        "comment": "Very tactile and responsive. Build quality is solid. One star off because the spacebar was a bit squeaky out of the box.",
        "image_base64": None,
        "status": "approved",
        "username": "code_ninja",
        "created_at": "2026-11-03 14:15:00"
    },
    {
        "id": 3,
        "product_id": 2,
        "rating": 5,
        "comment": "Best travel mouse ever. Battery life is incredible and fits perfectly in my hand.",
        "image_base64": None,
        "status": "approved",
        "username": "digital_nomad",
        "created_at": "2026-11-05 09:00:00"
    },
    {
        "id": 4,
        "product_id": 3,
        "rating": 5,
        "comment": "Outstanding noise cancelling. I can finally work in peace at busy coffee shops.",
        "image_base64": None,
        "status": "pending",
        "username": "focus_seeker",
        "created_at": "2026-11-06 11:20:00"
    }
]

