from dotenv import load_dotenv
from secrets import token_hex
import os

load_dotenv()


class Settings:
    APP_NAME = os.environ.get("APP_NAME", "Threshold")
    APP_VERSION = os.environ.get("APP_VERSION", "1.0.1")
    PORT = os.environ.get("PORT", 5000)
    HOST = os.environ.get("HOST", "0.0.0.0")
    DEBUG_MODE = os.environ.get("DEBUG_MODE", False)
    SECRET_KEY = os.environ.get("SECRET_KEY", token_hex(64))

    DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///blog_data.db")

    # Allow insecure HTTP connections for local testing
    OAUTHLIB_INSECURE_TRANSPORT = "1"
