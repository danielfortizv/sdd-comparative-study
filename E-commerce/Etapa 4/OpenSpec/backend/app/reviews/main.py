import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import json
import uuid
import time
import threading
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import pika

from app.auth import verify_access_token
from app.schemas import ReviewCreate, ReviewOut, ModerationAction

DATABASE_URL = os.getenv("REVIEWS_DATABASE_URL", "sqlite:///./reviews.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False)
    user_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=False)
    image_data = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Outbox(Base):
    __tablename__ = "outbox"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    correlation_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String, default="pending", nullable=False) # pending, published
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Reviews & Moderation Microservice",
    description="Manages product reviews, moderation, and exports outbox events.",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please sign in again.",
        )
    return user_id

# RabbitMQ configuration from stage4-runtime.json or default env
AMQP_URL = os.environ.get("AMQP_URL", "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_openspec")
EVENT_NAMESPACE = os.environ.get("EVENT_NAMESPACE", "stage4.openspec")

def publish_outbox_events():
    """Background worker that continuously polls the outbox and publishes to RabbitMQ."""
    print("Outbox publisher thread started.")
    connection = None
    channel = None
    
    while True:
        try:
            # Setup connection with backoff
            if connection is None or connection.is_closed:
                print(f"Connecting to RabbitMQ at {AMQP_URL}...")
                parameters = pika.URLParameters(AMQP_URL)
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                # Declare fanout exchange for reliability
                channel.exchange_declare(exchange=EVENT_NAMESPACE, exchange_type='fanout', durable=True)
                channel.confirm_delivery() # Enable publisher confirmations
                print("Connected to RabbitMQ successfully.")

            db = SessionLocal()
            try:
                pending_events = db.query(Outbox).filter(Outbox.status == "pending").order_by(Outbox.id.asc()).all()
                for event in pending_events:
                    payload_dict = json.loads(event.payload)
                    message = {
                        "event_id": event.event_id,
                        "correlation_id": event.correlation_id,
                        "event_type": event.event_type,
                        "timestamp": event.created_at.isoformat() + "Z",
                        "payload": payload_dict
                    }
                    
                    # Publish with confirmation
                    try:
                        channel.basic_publish(
                            exchange=EVENT_NAMESPACE,
                            routing_key='',
                            body=json.dumps(message),
                            properties=pika.BasicProperties(
                                delivery_mode=2, # make message durable
                                content_type='application/json',
                                message_id=event.event_id
                            )
                        )
                        # On this pika version, success is indicated by returning without throwing an exception
                        event.status = "published"
                        db.commit()
                        print(f"Published event {event.event_id} successfully (confirmed).")
                    except pika.exceptions.UnroutableError:
                        print(f"Event {event.event_id} was unroutable.")
                    except Exception as pub_ex:
                        print(f"Failed to publish event {event.event_id}: {pub_ex}")
                        raise pub_ex
            except Exception as db_ex:
                print(f"Error reading outbox in worker: {db_ex}")
                db.rollback()
            finally:
                db.close()
                
            time.sleep(1.0) # Poll every second
            
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ connection lost/failed. Retrying in 5 seconds...")
            connection = None
            channel = None
            time.sleep(5.0)
        except Exception as e:
            print(f"Unexpected error in outbox worker: {e}. Retrying in 5 seconds...")
            connection = None
            channel = None
            time.sleep(5.0)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # Start outbox publisher in background
    t = threading.Thread(target=publish_outbox_events, daemon=True)
    t.start()

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy", "service": "reviews"}

@app.post("/api/products/{id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def submit_review(
    id: int,
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # In reviews service, we accept reviews for any product ID without synchronous catalog checking
    new_review = Review(
        product_id=id,
        user_id=current_user,
        rating=review_data.rating,
        comment=review_data.comment,
        image_data=review_data.image_data,
        status="pending"
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

@app.get("/api/moderation/reviews", response_model=list[ReviewOut])
def list_pending_reviews(
    response: Response,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    if current_user != "moderator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the moderator can access this resource."
        )
    pending_reviews = db.query(Review).filter(Review.status == "pending").order_by(Review.created_at.desc()).all()
    return pending_reviews

@app.post("/api/moderation/reviews/{review_id}/action", response_model=ReviewOut)
def moderate_review(
    review_id: int,
    action_data: ModerationAction,
    response: Response,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    if current_user != "moderator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the moderator can moderate reviews."
        )
    
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found."
        )
    
    action = action_data.action.lower().strip()
    if action == "approve":
        review.status = "approved"
    elif action == "reject":
        review.status = "rejected"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve' or 'reject'."
        )
    
    # Create Event and write to outbox in the same transaction
    event_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    payload = {
        "review_id": review.id,
        "product_id": review.product_id,
        "user_id": review.user_id,
        "rating": review.rating,
        "comment": review.comment,
        "image_data": review.image_data,
        "status": review.status
    }
    
    outbox_entry = Outbox(
        event_id=event_id,
        correlation_id=correlation_id,
        event_type="review_moderated",
        payload=json.dumps(payload),
        status="pending"
    )
    
    db.add(outbox_entry)
    db.commit()
    db.refresh(review)
    return review

if __name__ == "__main__":
    uvicorn.run("app.reviews.main:app", host=os.getenv("REVIEWS_HOST", "127.0.0.1"), port=int(os.getenv("REVIEWS_PORT", 18003)))
