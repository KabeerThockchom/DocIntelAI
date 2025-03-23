import os
import json
import uuid
import time
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime
from collections import Counter

from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DocxParser
from app.parsers.pptx_parser import PPTXParser
from app.parsers.excel_parser import ExcelParser
from app.chunking.chunker import DocumentChunker
from app.embeddings.embedder import AzureOpenAIEmbedder
from app.storage.chroma_db import ChromaDBStorage
from app.utils.logging import log_step, Timer


router = APIRouter()

# Initialize components
chunker = DocumentChunker()
chroma_db = ChromaDBStorage()
embedder = AzureOpenAIEmbedder()

# Configure thread pool for parallel processing
# Using a thread pool with a reasonable number of workers
# based on the high API limits (20,000 requests per minute)
MAX_WORKERS = 10
thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)


# Models
class DocumentMetadata(BaseModel):
    """Document metadata for upload."""
    created_by: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    additional_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    """Request for querying documents."""
    query: str
    n_results: int = 5
    filter_criteria: Optional[Dict[str, Any]] = None


class StatisticsResponse(BaseModel):
    """Statistics about the document processing system."""
    total_documents: int
    document_types: Dict[str, int]
    total_chunks: int
    total_ocr_chunks: int
    ocr_percentage: float
    avg_chunks_per_document: float


class DocumentSummary(BaseModel):
    """Summary information about a document."""
    document_id: str
    filename: str
    document_type: str
    total_chunks: int
    created_at: str
    ocr_used: bool = False
    tags: List[str] = Field(default_factory=list)


class DocumentDetail(BaseModel):
    """Detailed information about a document."""
    document_id: str
    filename: str
    document_type: str
    total_chunks: int
    created_at: str
    ocr_used: bool = False
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunks: List[Dict[str, Any]] = Field(default_factory=list)


# Routes
@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    parallel_processing: bool = Form(True)  # Enable parallel processing by default
):
    """
    Upload and process a document.
    
    Args:
        background_tasks: Background tasks
        file: Uploaded file
        metadata: Document metadata as JSON string
        parallel_processing: Whether to use parallel processing
    
    Returns:
        Document processing status
    """
    try:
        # Parse metadata
        doc_metadata = None
        if metadata:
            doc_metadata = json.loads(metadata)
        
        # Create uploads directory structure if it doesn't exist
        uploads_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Create a user-specific directory (use 'default' if no user specified)
        user_id = doc_metadata.get("created_by", "default") if doc_metadata else "default"
        user_dir = os.path.join(uploads_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Generate a unique filename to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(user_dir, unique_filename)
        
        # Save the file permanently
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        log_step("Document Upload", f"Saved file to {file_path}")
        
        # Get file extension
        file_ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
        
        # Update metadata with file path
        if doc_metadata is None:
            doc_metadata = {}
        doc_metadata["file_path"] = file_path
        
        # Process document based on file type
        if file_ext == "pdf":
            parser = PDFParser(chunker)
        elif file_ext == "docx":
            parser = DocxParser(chunker)
        elif file_ext == "pptx":
            parser = PPTXParser(chunker)
        elif file_ext in ["xlsx", "xls", "csv"]:
            parser = ExcelParser(chunker)
        else:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
        
        # Schedule document processing as background task
        if parallel_processing:
            background_tasks.add_task(
                process_document_parallel,
                file_path,
                file.filename,
                doc_metadata
            )
        else:
            background_tasks.add_task(
                process_document,
                file_path,
                file.filename,
                doc_metadata
            )
        
        return {"status": "processing", "filename": file.filename, "parallel_processing": parallel_processing}
    
    except Exception as e:
        log_step("Document Upload", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_documents(query_request: QueryRequest):
    """
    Query documents.
    
    Args:
        query_request: Query request
    
    Returns:
        Query results
    """
    try:
        with Timer("Document Query"):
            # Generate embedding for query
            query_embeddings = embedder.generate_embeddings([get_dummy_chunk(query_request.query)])
            
            if not query_embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate query embedding")
            
            query_embedding = list(query_embeddings.values())[0]
            
            # Query ChromaDB
            results = chroma_db.query_similar(
                query_text=query_request.query,
                embedding=query_embedding,
                n_results=query_request.n_results,
                filter_criteria=query_request.filter_criteria
            )
            
            return {"results": results}
    
    except Exception as e:
        log_step("Document Query", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document.
    
    Args:
        document_id: Document ID
    
    Returns:
        Deletion status
    """
    try:
        success = chroma_db.delete_document(document_id)
        
        if success:
            return {"status": "success", "message": f"Document {document_id} deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document")
    
    except Exception as e:
        log_step("Document Delete", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_documents(
    document_type: Optional[str] = Query(None, description="Filter by document type (pdf, docx, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of documents per page")
):
    """
    List all documents in the system.
    
    Args:
        document_type: Optional filter by document type
        page: Page number (1-indexed)
        page_size: Number of documents per page
    
    Returns:
        List of document summaries
    """
    try:
        with Timer("List Documents"):
            # Get unique document IDs and metadata from ChromaDB
            filter_criteria = {}
            if document_type:
                filter_criteria["source_document_type"] = document_type
                
            documents = chroma_db.list_documents(filter_criteria)
            
            # Calculate pagination
            total_documents = len(documents)
            total_pages = (total_documents + page_size - 1) // page_size
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_documents = documents[start_idx:end_idx]
            
            # Convert to DocumentSummary objects
            document_summaries = []
            for doc in paginated_documents:
                # Extract tags if available
                tags = []
                if "tags" in doc.get("metadata", {}):
                    tags = doc["metadata"]["tags"]
                
                document_summaries.append(DocumentSummary(
                    document_id=doc["document_id"],
                    filename=doc["filename"],
                    document_type=doc["document_type"],
                    total_chunks=doc["chunk_count"],
                    created_at=doc["created_at"],
                    ocr_used=doc["ocr_used"],
                    tags=tags
                ))
            
            return {
                "documents": document_summaries,
                "pagination": {
                    "total": total_documents,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
            }
    
    except Exception as e:
        log_step("List Documents", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_system_statistics():
    """
    Get statistics about the document processing system.
    
    Returns:
        System statistics
    """
    try:
        with Timer("System Statistics"):
            # Get document statistics from ChromaDB
            documents = chroma_db.list_documents()
            
            # Count document types
            document_types = Counter([doc["document_type"] for doc in documents])
            
            # Count total chunks and OCR chunks
            total_chunks = sum(doc["chunk_count"] for doc in documents)
            ocr_chunks = sum(doc.get("ocr_chunk_count", 0) for doc in documents)
            
            # Calculate average chunks per document and OCR percentage
            avg_chunks = total_chunks / len(documents) if documents else 0
            ocr_percentage = (ocr_chunks / total_chunks * 100) if total_chunks > 0 else 0
            
            return StatisticsResponse(
                total_documents=len(documents),
                document_types=dict(document_types),
                total_chunks=total_chunks,
                total_ocr_chunks=ocr_chunks,
                ocr_percentage=ocr_percentage,
                avg_chunks_per_document=avg_chunks
            )
    
    except Exception as e:
        log_step("System Statistics", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document_details(
    document_id: str,
    include_chunks: bool = Query(False, description="Include document chunks in response")
):
    """
    Get detailed information about a document.
    
    Args:
        document_id: Document ID
        include_chunks: Whether to include document chunks in response
    
    Returns:
        Document details
    """
    try:
        with Timer("Document Details"):
            # Get document metadata from ChromaDB
            document = chroma_db.get_document(document_id)
            
            if not document:
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
            
            # Extract tags if available
            tags = []
            if "tags" in document.get("metadata", {}):
                tags = document["metadata"]["tags"]
            
            # Get document chunks if requested
            chunks = []
            if include_chunks:
                chunks = chroma_db.get_document_chunks(document_id)
            
            return DocumentDetail(
                document_id=document["document_id"],
                filename=document["filename"],
                document_type=document["document_type"],
                total_chunks=document["chunk_count"],
                created_at=document["created_at"],
                ocr_used=document["ocr_used"],
                tags=tags,
                metadata=document.get("metadata", {}),
                chunks=chunks
            )
    
    except HTTPException:
        raise
    except Exception as e:
        log_step("Document Details", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/file")
async def get_document_file(document_id: str, page: int = Query(None, description="Page number to navigate to")):
    try:
        # Get document from ChromaDB instead of database
        document = chroma_db.get_document(document_id)
        if not document:
            logging.error(f"Document not found: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")

        # Check if file_path is in metadata
        file_path = None
        if document.get("metadata") and "file_path" in document.get("metadata", {}):
            file_path = document["metadata"]["file_path"]
            logging.info(f"Found file path in metadata: {file_path}")
        elif "file_path" in document:
            file_path = document["file_path"]
            logging.info(f"Found file path in document: {file_path}")
        
        if not file_path or not os.path.exists(file_path):
            logging.info(f"File path not found or file doesn't exist at {file_path}. Searching in uploads directory...")
            
            # Try to find the file in the uploads directory and its subdirectories
            uploads_dir = os.path.join(os.getcwd(), "uploads")
            if not os.path.exists(uploads_dir):
                # Try relative path if absolute path doesn't exist
                uploads_dir = os.path.join("docintel", "uploads")
                if not os.path.exists(uploads_dir):
                    uploads_dir = "uploads"
            
            logging.info(f"Searching for files in uploads directory: {uploads_dir}")
            
            # First try to find a file with the document ID in the name
            for root, dirs, files in os.walk(uploads_dir):
                for filename in files:
                    if document_id in filename:
                        file_path = os.path.join(root, filename)
                        logging.info(f"Found file by document ID: {file_path}")
                        break
                if file_path and os.path.exists(file_path):
                    break
            
            # If not found by ID, try to find by the document's filename if available
            if (not file_path or not os.path.exists(file_path)) and document.get("filename"):
                for root, dirs, files in os.walk(uploads_dir):
                    for filename in files:
                        # Check for exact match or if the document filename is contained in the file
                        if document["filename"] == filename or document["filename"] in filename:
                            file_path = os.path.join(root, filename)
                            logging.info(f"Found file by filename: {file_path}")
                            break
                    if file_path and os.path.exists(file_path):
                        break
            
            if not file_path or not os.path.exists(file_path):
                logging.error(f"File not found for document: {document_id}")
                raise HTTPException(status_code=404, detail="File not found")
        
        # Get file name from path
        file_name = os.path.basename(file_path)
        
        # Determine content type based on file extension
        file_extension = os.path.splitext(file_path)[1].lower()
        content_type = "application/octet-stream"  # Default content type
        
        # Map common extensions to content types
        content_type_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png"
        }
        
        if file_extension in content_type_map:
            content_type = content_type_map[file_extension]
        
        logging.info(f"Returning file: {file_path} with content type: {content_type}")
        
        # Set headers for proper file handling
        headers = {
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Access-Control-Expose-Headers": "Content-Disposition, X-PDF-Page",
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "ETag": f'"{os.path.getmtime(file_path)}"'  # Use file modification time as ETag
        }
        
        # For PDF files, if a page number is specified, add it to the response headers
        if file_extension.lower() == '.pdf' and page is not None:
            headers["X-PDF-Page"] = str(page)
            # Add fragment identifier for direct page navigation
            headers["Content-Disposition"] = f'inline; filename="{file_name}#page={page}"'
        
        return FileResponse(
            path=file_path,
            media_type=content_type,
            headers=headers,
            filename=file_name
        )
    except Exception as e:
        logging.error(f"Error retrieving document file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving document file: {str(e)}")


@router.get("/{document_id}/highlighted")
async def get_highlighted_document(document_id: str, chunk_id: str = Query(..., description="Chunk ID to highlight")):
    """
    Get the original document for the specified chunk.
    
    Args:
        document_id: Document ID
        chunk_id: Chunk ID
        
    Returns:
        Original document file as a streaming response
    """
    try:
        # Get document details
        document = chroma_db.get_document(document_id)
        if not document:
            log_step("Get Document", f"Document {document_id} not found", level="error")
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get file path from metadata
        file_path = document.get("metadata", {}).get("file_path")
        
        # Also check if file_path is directly in the document
        if not file_path and "file_path" in document:
            file_path = document["file_path"]
            
        if not file_path:
            # Try to find the file in the uploads directory
            uploads_dir = os.path.join(os.getcwd(), "uploads")
            filename = document.get("filename")
            
            if filename:
                # Search for the file in the uploads directory and its subdirectories
                for root, dirs, files in os.walk(uploads_dir):
                    if filename in files:
                        file_path = os.path.join(root, filename)
                        log_step("Get Document", f"Found file at {file_path}")
                        break
                        
                # If still not found, search for files with similar names
                if not file_path:
                    for root, dirs, files in os.walk(uploads_dir):
                        for file in files:
                            if filename in file:
                                file_path = os.path.join(root, file)
                                log_step("Get Document", f"Found similar file at {file_path}")
                                break
                        if file_path:
                            break
            
            if not file_path:
                log_step("Get Document", f"File path not found for document {document_id}", level="error")
                raise HTTPException(status_code=404, detail="Document file not found")
        
        # Check if file exists
        if not os.path.exists(file_path):
            log_step("Get Document", f"File {file_path} not found on disk", level="error")
            raise HTTPException(status_code=404, detail="Document file not found on disk")
        
        # Return the original document
        return FileResponse(
            path=file_path,
            filename=document.get("filename", f"document_{document_id}"),
            media_type=get_media_type_for_document(document.get("document_type", ""))
        )
    except Exception as e:
        log_step("Get Document", f"Error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")


def get_media_type_for_document(document_type: str) -> str:
    """
    Get the appropriate media type for a document type.
    
    Args:
        document_type: Document type (pdf, docx, etc.)
        
    Returns:
        Media type string
    """
    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "ppt": "application/vnd.ms-powerpoint",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "csv": "text/csv",
        "txt": "text/plain",
        "json": "application/json",
        "html": "text/html",
        "htm": "text/html",
        "xml": "application/xml",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "svg": "image/svg+xml"
    }
    
    return media_types.get(document_type.lower(), "application/octet-stream")


# Helper functions
async def process_document_parallel(file_path: str, filename: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Process a document in the background with parallel processing.
    
    Args:
        file_path: Path to the document file
        filename: Original filename
        metadata: Additional metadata
    """
    try:
        with Timer(f"Process Document {filename} (Parallel)"):
            log_step("Document Processing", f"Processing document: {filename} with parallel processing")
            
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
            
            # Parse document based on file type
            if file_ext == "pdf":
                parser = PDFParser(chunker)
                processed_doc = parser.parse(file_path, filename, metadata)
            elif file_ext == "docx":
                parser = DocxParser(chunker)
                processed_doc = parser.parse(file_path, filename, metadata)
            elif file_ext == "pptx":
                parser = PPTXParser(chunker)
                processed_doc = parser.parse(file_path, filename, metadata)
            elif file_ext in ["xlsx", "xls", "csv"]:
                parser = ExcelParser(chunker)
                processed_doc = parser.parse(file_path, filename, metadata)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Generate embeddings for chunks asynchronously
            embeddings = await embedder.generate_embeddings_async(processed_doc.chunks)
            
            # Store document and embeddings
            document_id = chroma_db.store_document(processed_doc, embeddings)
            
            log_step("Document Processing", f"Completed processing document: {filename} with parallel processing")
            
    except Exception as e:
        log_step("Document Processing", f"Error processing document {filename} with parallel processing: {str(e)}", level="error")


def process_document(file_path: str, filename: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Process a document in the background.
    
    Args:
        file_path: Path to the document file
        filename: Original filename
        metadata: Additional metadata
    """
    try:
        with Timer(f"Process Document {filename}"):
            log_step("Document Processing", f"Processing document: {filename}")
            
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
            
            # Parse document based on file type
            if file_ext == "pdf":
                parser = PDFParser(chunker)
                processed_doc = parser.parse(file_path, filename, metadata)
            elif file_ext == "docx":
                parser = DocxParser(chunker)
                processed_doc = parser.parse(file_path, filename, metadata)
            elif file_ext == "pptx":
                parser = PPTXParser(chunker)
                processed_doc = parser.parse(file_path, filename, metadata)
            elif file_ext in ["xlsx", "xls", "csv"]:
                parser = ExcelParser(chunker)
                processed_doc = parser.parse(file_path, filename, metadata)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Generate embeddings for chunks
            embeddings = embedder.generate_embeddings(processed_doc.chunks)
            
            # Store document and embeddings
            document_id = chroma_db.store_document(processed_doc, embeddings)
            
            log_step("Document Processing", f"Completed processing document: {filename}")
            
    except Exception as e:
        log_step("Document Processing", f"Error processing document {filename}: {str(e)}", level="error")


def get_dummy_chunk(text: str) -> Any:
    """
    Create a dummy document chunk for embedding generation.
    
    Args:
        text: Text to embed
        
    Returns:
        Dummy document chunk
    """
    # Import here to avoid circular import
    from app.chunking.models import DocumentChunk
    
    return DocumentChunk(
        text=text,
        metadata={},
        source_document_id="query",
        source_document_name="query",
        source_document_type="query"
    )