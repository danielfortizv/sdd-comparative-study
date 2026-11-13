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
