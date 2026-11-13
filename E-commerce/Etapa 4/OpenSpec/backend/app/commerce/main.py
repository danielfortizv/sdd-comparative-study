import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import json
import time
import threading
import uvicorn
from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import pika

from app.schemas import ProductOut, ProductDetailOut, ReviewOut
from app.cache import cache_instance

DATABASE_URL = os.getenv("COMMERCE_DATABASE_URL", "sqlite:///./commerce.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)

class PublicReview(Base):
    __tablename__ = "public_reviews"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    user_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=False)
    image_data = Column(String, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)

class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id = Column(String, primary_key=True, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Commerce & Catalog Microservice",
    description="Manages product catalog and consumes public review events for its projection.",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RabbitMQ configuration
AMQP_URL = os.environ.get("AMQP_URL", "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_openspec")
EVENT_NAMESPACE = os.environ.get("EVENT_NAMESPACE", "stage4.openspec")

def seed_products(db: Session):
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
        print("Demo products seeded in commerce database.")

retry_counts = {}

def consume_review_events():
    """Background consumer that subscribes to reviews moderation events with bounded retry/DLQ."""
    print("Events consumer thread started.")
    queue_name = os.environ.get("QUEUE_NAME", "commerce_review_projection_queue")
    connection = None
    channel = None
    
    while True:
        try:
            if connection is None or connection.is_closed:
                print(f"Consumer connecting to RabbitMQ at {AMQP_URL}...")
                parameters = pika.URLParameters(AMQP_URL)
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                
                # Declare exchange
                channel.exchange_declare(exchange=EVENT_NAMESPACE, exchange_type='fanout', durable=True)
                
                # Declare Dead Letter Exchange (DLX) and Dead Letter Queue (DLQ)
                dlx_name = f"{EVENT_NAMESPACE}.dlx"
                dlq_name = f"{queue_name}_dlq"
                channel.exchange_declare(exchange=dlx_name, exchange_type='direct', durable=True)
                channel.queue_declare(queue=dlq_name, durable=True)
                channel.queue_bind(exchange=dlx_name, queue=dlq_name, routing_key=queue_name)
                
                # Declare and bind main queue with DLX configuration (non-destructive)
                arguments = {
                    "x-dead-letter-exchange": dlx_name,
                    "x-dead-letter-routing-key": queue_name
                }
                try:
                    channel.queue_declare(queue=queue_name, durable=True, arguments=arguments)
                    channel.queue_bind(exchange=EVENT_NAMESPACE, queue=queue_name)
                except (pika.exceptions.ChannelClosedByBroker, pika.exceptions.AMQPChannelError) as chan_err:
                    print(f"Precondition or Channel error during queue declaration ({chan_err}). Attempting to migrate by deleting and redeclaring...")
                    try:
                        # Re-establish channel since the previous one was closed by the broker
                        channel = connection.channel()
                        channel.queue_delete(queue=queue_name)
                        print(f"Deleted outdated queue: {queue_name}")
                        # Redeclare
                        channel.queue_declare(queue=queue_name, durable=True, arguments=arguments)
                        channel.queue_bind(exchange=EVENT_NAMESPACE, queue=queue_name)
                        print(f"Successfully redeclared queue: {queue_name}")
                    except Exception as mig_ex:
                        print(f"Migration queue declaration failed: {mig_ex}")
                        raise mig_ex
                
                print("Connected to RabbitMQ and main queue configured with DLX/DLQ.")

            def callback(ch, method, properties, body):
                event_id = "unknown"
                try:
                    event_data = json.loads(body.decode('utf-8'))
                    event_id = event_data.get("event_id", "unknown")
                    payload = event_data.get("payload", {})
                    
                    product_id = payload.get("product_id")
                    review_id = payload.get("review_id")
                    status_str = payload.get("status")

                    print(f"Received event {event_id}: review {review_id} for product {product_id} ({status_str})")
                    
                    db = SessionLocal()
                    try:
                        # Idempotency Check
                        existing_event = db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()
                        if existing_event:
                            print(f"Event {event_id} already processed. Skipping.")
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                            if event_id in retry_counts:
                                del retry_counts[event_id]
                            return

                        # Process Event
                        if status_str == "approved":
                            # Create or update PublicReview projection
                            existing_review = db.query(PublicReview).filter(PublicReview.id == review_id).first()
                            if not existing_review:
                                # Convert ISO created_at string
                                created_at_dt = datetime.utcnow()
                                if event_data.get("timestamp"):
                                    try:
                                        created_at_dt = datetime.fromisoformat(event_data["timestamp"].replace("Z", "+00:00"))
                                    except Exception:
                                        pass
                                
                                new_review = PublicReview(
                                    id=review_id,
                                    product_id=product_id,
                                    user_id=payload.get("user_id"),
                                    rating=payload.get("rating"),
                                    comment=payload.get("comment"),
                                    image_data=payload.get("image_data"),
                                    status=status_str,
                                    created_at=created_at_dt
                                )
                                db.add(new_review)
                            else:
                                existing_review.status = status_str
                        elif status_str == "rejected":
                            # Remove from projection or update to rejected
                            db.query(PublicReview).filter(PublicReview.id == review_id).delete()

                        # Register processed event ID
                        proc_event = ProcessedEvent(event_id=event_id)
                        db.add(proc_event)
                        db.commit()
                        print(f"Event {event_id} processed successfully.")
                        
                        # Invalidate local caches
                        cache_instance.invalidate_key("products_list")
                        cache_instance.invalidate_key(f"product_detail_{product_id}")
                        cache_instance.invalidate_key(f"product_reviews_{product_id}")
                        print(f"Caches invalidated for product {product_id}")
                        
                        if event_id in retry_counts:
                            del retry_counts[event_id]
                    except Exception as db_ex:
                        print(f"Database error while processing event {event_id}: {db_ex}")
                        db.rollback()
                        raise db_ex
                    finally:
                        db.close()
                    
                    # Manually acknowledge on successful process
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as cb_ex:
                    print(f"Callback processing error for event {event_id}: {cb_ex}")
                    # Bounded retry: increment count
                    if event_id != "unknown":
                        retry_counts[event_id] = retry_counts.get(event_id, 0) + 1
                        attempts = retry_counts[event_id]
                        if attempts < 3:
                            print(f"Retrying event {event_id} (attempt {attempts}/3)...")
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                        else:
                            print(f"Event {event_id} failed {attempts} attempts. Sending to DLQ via reject/no-requeue.")
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                            del retry_counts[event_id]
                    else:
                        # Malformed body, reject immediately without requeue
                        print("Malformed message body. Rejecting to DLQ immediately.")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
            print("Started consuming RabbitMQ events.")
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ connection lost/failed in consumer. Retrying in 5 seconds...")
            connection = None
            channel = None
            time.sleep(5.0)
        except Exception as e:
            print(f"Unexpected error in events consumer: {e}. Retrying in 5 seconds...")
            connection = None
            channel = None
            time.sleep(5.0)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_products(db)
    finally:
        db.close()
    
    # Start RabbitMQ consumer thread
    t = threading.Thread(target=consume_review_events, daemon=True)
    t.start()

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy", "service": "commerce"}

@app.get("/api/products", response_model=List[ProductOut])
def get_products(db: Session = Depends(get_db)):
    cache_key = "products_list"
    cached = cache_instance.get(cache_key)
    if cached is not None:
        return cached

    products = db.query(Product).all()
    result = [ProductOut.model_validate(p).model_dump() for p in products]
    cache_instance.set(cache_key, result, ttl_seconds=60)
    return result

@app.get("/api/products/{id}", response_model=ProductDetailOut)
def get_product_detail(id: int, db: Session = Depends(get_db)):
    cache_key = f"product_detail_{id}"
    cached = cache_instance.get(cache_key)
    if cached is not None:
        return cached

    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found."
        )
    
    approved_reviews = db.query(PublicReview).filter(
        PublicReview.product_id == id, 
        PublicReview.status == "approved"
    ).all()
    
    avg_rating = None
    if approved_reviews:
        avg_rating = sum(r.rating for r in approved_reviews) / len(approved_reviews)
        avg_rating = round(avg_rating, 2)
    
    result = {
        "id": product.id,
        "name": product.name,
        "image_url": product.image_url,
        "description": product.description,
        "price": product.price,
        "is_available": product.is_available,
        "average_rating": avg_rating
    }
    cache_instance.set(cache_key, result, ttl_seconds=60)
    return result

@app.get("/api/products/{id}/reviews", response_model=List[ReviewOut])
def get_product_reviews(id: int, db: Session = Depends(get_db)):
    cache_key = f"product_reviews_{id}"
    cached = cache_instance.get(cache_key)
    if cached is not None:
        return cached

    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found."
        )
    
    reviews = db.query(PublicReview).filter(
        PublicReview.product_id == id, 
        PublicReview.status == "approved"
    ).order_by(PublicReview.created_at.desc()).all()
    
    result = [ReviewOut.model_validate(r).model_dump() for r in reviews]
    cache_instance.set(cache_key, result, ttl_seconds=60)
    return result

if __name__ == "__main__":
    uvicorn.run("app.commerce.main:app", host=os.getenv("COMMERCE_HOST", "127.0.0.1"), port=int(os.getenv("COMMERCE_PORT", 18002)))
