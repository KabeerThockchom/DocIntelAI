import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Inkling API",
    description="API for parsing, chunking, embedding, retrieving, and chatting with document content",
    version="1.0.0",
)

# Configure CORS - list specific origins instead of wildcard
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
    # Add any other origins that need access
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Queue-ID", "X-Realtime-Stream", "Content-Type", "Content-Length"],
)

# Import routes
from app.routes import document_routes, drive_routes, chat_routes

# Include routers
app.include_router(document_routes.router, prefix="/api/documents", tags=["Documents"])
app.include_router(drive_routes.router, prefix="/api/drive", tags=["Google Drive"])
app.include_router(chat_routes.router, prefix="/api/chat", tags=["Chat"])

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Inkling API is running"}

# Path to the frontend build directory
current_file = Path(__file__)
build_path = current_file.parent / "build"

# Check if the static directory exists
static_path = build_path / "static"
if static_path.exists():
    # Mount the static files directory
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
else:
    print(f"WARNING: Static directory does not exist at {static_path}")

# Check if there are any other static assets at the root level
for item in build_path.glob("*"):
    if item.is_file() and item.name not in ["index.html"]:
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
        return FileResponse(str(index_path))
    else:
        raise HTTPException(status_code=404, detail=f"Frontend files not found at {index_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)