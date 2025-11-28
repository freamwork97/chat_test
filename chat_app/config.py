import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "chatapp")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "messages")

POSTGRES_URL = os.getenv(
    "POSTGRES_URL", "postgresql+psycopg://postgres:postgres@postgres:5432/chatapp"
)

FRONTEND_DIST = os.path.join("frontend", "dist")

# Directory where uploaded files are stored and served from.
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join("uploads"))
