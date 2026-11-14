from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    app_name: str = "Tetris Study Stage 3 Option A"
    debug: bool = False
    tetris_db_path: str = "./data/high-scores.sqlite3"
    # RESTRICTIVE CORS POLICY: No wildcards with credentials. List allowed origins explicitly.
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:5183",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5183"
    ]

    @field_validator("cors_origins", mode="after")
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        # Reject/sanitize wildcard origins when credentials are enabled
        for origin in v:
            if origin == "*" or origin.strip() == "*":
                raise ValueError("Wildcard CORS origin '*' is not allowed when credentials are enabled.")
        return v

settings = Settings()
