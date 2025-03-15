from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class DocumentChunk(BaseModel):
    """Represents a chunk of a document with metadata."""
    
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Source document information
    source_document_id: str
    source_document_name: str
    source_document_type: str
    
    # Chunk location information
    page_number: Optional[int] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    
    # OCR-specific information (for complex documents)
    is_ocr: bool = False
    bounding_box: Optional[Dict[str, float]] = None
    
    # Heading structure
    heading_path: List[str] = Field(default_factory=list)
    heading_level: Optional[int] = None
    
    # File metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # User information
    created_by: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                "text": "This is a sample chunk of text from a document.",
                "metadata": {
                    "section": "Introduction",
                    "keywords": ["sample", "chunk", "document"]
                },
                "source_document_id": "doc123",
                "source_document_name": "example.pdf",
                "source_document_type": "pdf",
                "page_number": 1,
                "start_index": 0,
                "end_index": 46,
                "is_ocr": False,
                "heading_path": ["Chapter 1", "Introduction"],
                "heading_level": 2,
                "created_at": "2023-10-20T12:00:00",
                "updated_at": "2023-10-20T12:00:00",
                "created_by": "user@example.com"
            }
        }


class ProcessedDocument(BaseModel):
    """Represents a processed document with its chunks."""
    
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str
    file_size: int
    total_pages: Optional[int] = None
    total_chunks: int
    chunks: List[DocumentChunk]
    processing_time: float
    is_complex: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "example.pdf",
                "file_type": "pdf",
                "file_size": 1024000,
                "total_pages": 10,
                "total_chunks": 25,
                "chunks": [],  # Omitted for brevity
                "processing_time": 2.5,
                "is_complex": False,
                "created_at": "2023-10-20T12:00:00"
            }
        }