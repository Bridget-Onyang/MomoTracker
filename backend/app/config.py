"""Application settings, read from environment variables."""
import os

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./momotracker.db")