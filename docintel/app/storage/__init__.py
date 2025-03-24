# Storage Package
"""
Vector storage using Qdrant.
"""

from app.storage.qdrant_db import QdrantDBStorage
# For backward compatibility, alias QdrantDBStorage as ChromaDBStorage
ChromaDBStorage = QdrantDBStorage