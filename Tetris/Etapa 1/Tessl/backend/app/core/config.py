from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Tetris Study Stage 1 Option A"
    debug: bool = False

settings = Settings()
