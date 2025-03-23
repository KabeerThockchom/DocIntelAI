# Routes Package
"""
API routes for document processing and Google Drive integration.
"""

from app.routes.document_routes import router as document_router
from app.routes.drive_routes import router as drive_router
from app.routes.chat_routes import router as chat_router