import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./ecommerce.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    account_identifier = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Product).count() == 0:
            demo_products = [
                Product(
                    name="Classic Ceramic Mug",
                    image_url="https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&q=80&w=200",
                    description="A high-quality, elegant ceramic mug perfect for your daily hot beverages.",
                    price=12.99,
                    is_available=True
                ),
                Product(
                    name="Eco-Friendly Notebook",
                    image_url="https://images.unsplash.com/photo-1531346878377-a5be20888e57?auto=format&fit=crop&q=80&w=200",
                    description="Handcrafted with 100% recycled paper fibers, designed for creative minds.",
                    price=8.50,
                    is_available=True
                ),
                Product(
                    name="Minimalist Analog Watch",
                    image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=200",
                    description="Sleek and timeless timepiece with a comfortable premium leather band.",
                    price=85.00,
                    is_available=True
                ),
                Product(
                    name="Premium Wireless Earbuds",
                    image_url="https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&q=80&w=200",
                    description="Immersive crystal-clear sound with comfortable active noise-canceling.",
                    price=45.99,
                    is_available=False
                )
            ]
            db.add_all(demo_products)
            db.commit()
            print("Database successfully seeded with demo products.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()
