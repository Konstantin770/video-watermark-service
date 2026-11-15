import os
from redis import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

STORAGE_DIR = "/data"
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
PROCESSED_DIR = os.path.join(STORAGE_DIR, "processed")

redis_connection = Redis.from_url(REDIS_URL)
