import os
from dotenv import load_dotenv

# import redis

load_dotenv()


class ApplicationConfig:
    OPENAI_KEY = os.getenv("OPENAI_KEY")

    MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
    MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENV = os.getenv("PINECONE_ENV")

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    SECRET_KEY = os.getenv("SECRET_KEY")

    PG_USER = os.getenv("PG_USER")
    PG_PASS = os.getenv("PG_PASS")
    PG_HOST = os.getenv("PG_HOST")
    PG_DB = os.getenv("PG_DB")

    UPLOAD_FOLDER = "uploads"
