import os
from typing import List

class Settings:
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Web Calculator API"
    ALLOWED_ORIGINS: List[str] = ["*"]

settings = Settings()
