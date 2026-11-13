import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.auth import hash_password, verify_password, create_access_token
from app.schemas import UserAuth, UserOut, Token

DATABASE_URL = os.getenv("IDENTITY_DATABASE_URL", "sqlite:///./identity.db")

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Identity Microservice",
    description="Manages authentication and user accounts.",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.account_identifier == "moderator").count() == 0:
            moderator_user = User(
                account_identifier="moderator",
                password_hash=hash_password("modpassword")
            )
            db.add(moderator_user)
            db.commit()
            print("Moderator successfully seeded in identity database.")
    except Exception as e:
        print(f"Error seeding identity database: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy", "service": "identity"}

@app.post("/api/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_data: UserAuth, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    id_stripped = user_data.account_identifier.strip()
    pw_stripped = user_data.password.strip()

    if not id_stripped or not pw_stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account identifier and password are required and cannot be empty."
        )

    existing_user = db.query(User).filter(User.account_identifier == id_stripped).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account identifier is already in use. Please select a unique identifier."
        )

    hashed_pw = hash_password(user_data.password)
    new_user = User(account_identifier=id_stripped, password_hash=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=Token)
def login(user_data: UserAuth, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    id_stripped = user_data.account_identifier.strip()
    pw_stripped = user_data.password.strip()

    if not id_stripped or not pw_stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account identifier and password are required."
        )

    user = db.query(User).filter(User.account_identifier == id_stripped).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account identifier or password. Please verify your credentials."
        )

    token = create_access_token(account_identifier=user.account_identifier)
    return Token(access_token=token, account_identifier=user.account_identifier)

if __name__ == "__main__":
    uvicorn.run("app.identity.main:app", host=os.getenv("IDENTITY_HOST", "127.0.0.1"), port=int(os.getenv("IDENTITY_PORT", 18001)))
