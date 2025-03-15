import os
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.drive.google_drive import GoogleDriveClient
from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DocxParser
from app.chunking.chunker import DocumentChunker
from app.embeddings.embedder import AzureOpenAIEmbedder
from app.storage.chroma_db import ChromaDBStorage
from app.utils.logging import log_step, Timer


router = APIRouter()

# Initialize components
drive_client = GoogleDriveClient()
chunker = DocumentChunker()
chroma_db = ChromaDBStorage()
embedder = AzureOpenAIEmbedder()


# Models
class AuthRequest(BaseModel):
    """Request for authentication code."""
    code: str


class DriveFileRequest(BaseModel):
    """Request for processing a file from Google Drive."""
    file_id: str
    metadata: Optional[Dict[str, Any]] = None


class DriveFilesRequest(BaseModel):
    """Request for processing multiple files from Google Drive."""
    file_ids: List[str]
    metadata: Optional[Dict[str, Any]] = None


class DriveFolderRequest(BaseModel):
    """Request for processing a folder from Google Drive."""
    folder_id: str
    file_types: Optional[List[str]] = Field(default_factory=lambda: ["pdf", "docx", "pptx", "xlsx", "csv"])
    metadata: Optional[Dict[str, Any]] = None


# Routes
@router.get("/auth-url")
async def get_auth_url():
    """
    Get authorization URL for Google Drive.
    
    Returns:
        Authorization URL
    """
    try:
        auth_url = drive_client.get_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        log_step("Drive Auth", f"Error getting auth URL: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth")
async def authenticate(auth_request: AuthRequest):
    """
    Authenticate with Google Drive using authorization code.
    
    Args:
        auth_request: Authentication request
    
    Returns:
        Authentication status
    """
    try:
        success = drive_client.exchange_code(auth_request.code)
        
        if success:
            return {"status": "success", "message": "Authentication successful"}
        else:
            raise HTTPException(status_code=400, detail="Authentication failed")
    except Exception as e:
        log_step("Drive Auth", f"Error authenticating: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_files(folder_id: Optional[str] = None, file_types: Optional[str] = None):
    """
    List files in Google Drive.
    
    Args:
        folder_id: Folder ID to list files from (root folder if None)
        file_types: Comma-separated list of file extensions to filter by
    
    Returns:
        List of files
    """
    try:
        # Parse file types
        file_type_list = None
        if file_types:
            file_type_list = [ext.strip() for ext in file_types.split(",")]
        
        # List files
        files = drive_client.list_files(folder_id, file_type_list)
        return {"files": files}
    except Exception as e:
        log_step("Drive Files", f"Error listing files: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-file")
async def process_drive_file(request: DriveFileRequest):
    """
    Process a file from Google Drive.
    
    Args:
        request: Drive file request
    
    Returns:
        Processing status
    """
    try:
        with Timer("Process Drive File"):
            result = drive_client.process_file(request.file_id, request.metadata)
            return result
    except Exception as e:
        log_step("Drive File Processing", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-files")
async def process_drive_files(request: DriveFilesRequest):
    """
    Process multiple files from Google Drive.
    
    Args:
        request: Drive files request
    
    Returns:
        Processing status for each file
    """
    try:
        with Timer("Process Drive Files"):
            results = drive_client.process_files(request.file_ids, request.metadata)
            return {"results": results}
    except Exception as e:
        log_step("Drive Files Processing", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-folder")
async def process_drive_folder(
    background_tasks: BackgroundTasks,
    request: DriveFolderRequest
):
    """
    Process a folder from Google Drive.
    
    Args:
        background_tasks: Background tasks
        request: Drive folder request
    
    Returns:
        Processing status
    """
    try:
        # Schedule folder processing as background task
        background_tasks.add_task(
            process_drive_folder_task,
            request.folder_id,
            request.file_types,
            request.metadata
        )
        
        return {"status": "processing", "folder_id": request.folder_id}
    except Exception as e:
        log_step("Drive Folder Processing", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
def process_drive_file_task(file_id: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Process a file from Google Drive in the background.
    
    Args:
        file_id: Google Drive file ID
        metadata: Additional metadata
    """
    try:
        with Timer(f"Process Drive File {file_id}"):
            log_step("Drive File Processing", f"Processing file: {file_id}")
            
            # Download file from Google Drive
            file_data = drive_client.download_file(file_id)
            
            if not file_data:
                log_step("Drive File Processing", f"Failed to download file: {file_id}", level="error")
                return
            
            file_metadata = file_data["metadata"]
            file_content = file_data["content"]
            filename = file_metadata["name"]
            
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
            
            # Parse document based on file type
            if file_ext == "pdf":
                parser = PDFParser(chunker)
                processed_doc = parser.parse_stream(file_content, filename, metadata)
            elif file_ext == "docx":
                parser = DocxParser(chunker)
                processed_doc = parser.parse_stream(file_content, filename, metadata)
            else:
                log_step("Drive File Processing", f"Unsupported file type: {file_ext}", level="warning")
                return
            
            # Generate embeddings for chunks
            embeddings = embedder.generate_embeddings(processed_doc.chunks)
            
            # Store document and embeddings
            document_id = chroma_db.store_document(processed_doc, embeddings)
            
            log_step("Drive File Processing", f"Completed processing file: {filename}")
            
    except Exception as e:
        log_step("Drive File Processing", f"Error processing file {file_id}: {str(e)}", level="error")


def process_drive_folder_task(
    folder_id: str,
    file_types: List[str],
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Process a folder from Google Drive in the background.
    
    Args:
        folder_id: Google Drive folder ID
        file_types: List of file extensions to process
        metadata: Additional metadata
    """
    try:
        with Timer(f"Process Drive Folder {folder_id}"):
            log_step("Drive Folder Processing", f"Processing folder: {folder_id}")
            
            # List files in folder
            files = drive_client.list_files(folder_id, file_types)
            
            if not files:
                log_step("Drive Folder Processing", f"No files found in folder: {folder_id}", level="warning")
                return
            
            log_step("Drive Folder Processing", f"Found {len(files)} files to process")
            
            # Process each file
            for file in files:
                file_id = file["id"]
                
                try:
                    process_drive_file_task(file_id, metadata)
                except Exception as e:
                    log_step("Drive Folder Processing", f"Error processing file {file_id}: {str(e)}", level="error")
                    continue
            
            log_step("Drive Folder Processing", f"Completed processing folder: {folder_id}")
            
    except Exception as e:
        log_step("Drive Folder Processing", f"Error processing folder {folder_id}: {str(e)}", level="error")