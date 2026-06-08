import os

# Use a separate Qdrant path so pytest can run while uvicorn is using storage/qdrant_db
os.environ.setdefault("QDRANT_PATH", "storage/qdrant_test")
