import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="DocuIntel API",
    description="API for parsing, chunking, embedding, retrieving, and chatting with document content",
    version="1.0.0",
)

# Configure CORS - list specific origins instead of wildcard
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
    "http://localhost:3000",
    "https://*.onrender.com",  # Allow Render domains
    os.getenv("FRONTEND_URL", ""),  # Allow configurable frontend URL
]

# Filter out empty strings from origins
origins = [origin for origin in origins if origin]

logger.info(f"Configured CORS origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-User-ID"],
    expose_headers=["X-Queue-ID", "X-Realtime-Stream", "Content-Type", "Content-Length"],
)

# Add middleware to extract and validate user information
@app.middleware("http")
async def user_id_middleware(request: Request, call_next):
    # Extract user ID from headers if present
    user_id = request.headers.get("X-User-ID")
    if user_id:
        # Make user_id available to route handlers via request.state
        request.state.user_id = user_id
        logger.info(f"Request from user: {user_id}")
    else:
        request.state.user_id = None
        logger.info("Request from unauthenticated user")
    
    response = await call_next(request)
    return response

@app.on_event("startup")
async def startup_event():
    """Log important information on startup"""
    logger.info("Starting DocuIntel API")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Frontend URL: {os.getenv('FRONTEND_URL', 'not set')}")
    logger.info(f"Using OpenAI API: {bool(os.getenv('OPENAI_API_KEY'))}")
    logger.info(f"Using Supabase: {bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_KEY'))}")

# Import routes
from app.routes import document_routes, drive_routes, chat_routes

# Include routers
app.include_router(document_routes.router, prefix="/api/documents", tags=["Documents"])
app.include_router(drive_routes.router, prefix="/api/drive", tags=["Google Drive"])
app.include_router(chat_routes.router, prefix="/api/chat", tags=["Chat"])

@app.get("/healthz", tags=["Health"])
async def health_check():
    """Health check endpoint for Render."""
    return {"status": "ok", "message": "DocuIntel API is running"}

@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "DocuIntel API is running"}

# Path to the frontend build directory
current_file = Path(__file__)
build_path = current_file.parent / "build"

# Check if the static directory exists
static_path = build_path / "static"
if static_path.exists():
    # Mount the static files directory
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info(f"Mounted static files from {static_path}")
else:
    logger.warning(f"Static directory does not exist at {static_path}")

# Define direct routes for favicon files
@app.get("/favicon.ico")
async def get_favicon():
    favicon_path = build_path / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")

@app.get("/favicon-16x16.png")
async def get_favicon_16():
    favicon_path = build_path / "favicon-16x16.png"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon 16x16 not found")

@app.get("/favicon-32x32.png")
async def get_favicon_32():
    favicon_path = build_path / "favicon-32x32.png"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon 32x32 not found")

@app.get("/logo192.png")
async def get_logo_192():
    logo_path = build_path / "logo192.png"
    if logo_path.exists():
        return FileResponse(str(logo_path), media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo 192 not found")

@app.get("/logo512.png")
async def get_logo_512():
    logo_path = build_path / "logo512.png"
    if logo_path.exists():
        return FileResponse(str(logo_path), media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo 512 not found")

@app.get("/manifest.json")
async def get_manifest():
    manifest_path = build_path / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path), media_type="application/json")
    raise HTTPException(status_code=404, detail="Manifest not found")

# Check if there are any other static assets at the root level
for item in build_path.glob("*"):
    if item.is_file() and item.name not in ["index.html", "favicon.ico", "favicon-16x16.png", 
                                          "favicon-32x32.png", "logo192.png", "logo512.png", "manifest.json"]:
        # Mount individual files at root level
        app.mount(f"/{item.name}", StaticFiles(directory=str(build_path), html=True), name=item.name)

# Serve index.html for all other routes to support SPA routing
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # If the path starts with /api, it's not found (this shouldn't happen due to router order)
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Otherwise serve the index.html for client-side routing
    index_path = build_path / "index.html"
    
    if index_path.exists():
        logger.info(f"Serving index.html for path: {full_path}")
        return FileResponse(str(index_path))
    else:
        logger.error(f"Frontend files not found at {index_path}")
        raise HTTPException(status_code=404, detail=f"Frontend files not found at {index_path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)