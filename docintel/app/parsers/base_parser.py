from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional, BinaryIO
import os
import uuid
from datetime import datetime

from app.chunking.models import DocumentChunk, ProcessedDocument
from app.utils.logging import log_step, Timer


class BaseDocumentParser(ABC):
    """Base class for all document parsers."""
    
    def __init__(self):
        self.document_id = str(uuid.uuid4())
    
    @abstractmethod
    def parse(
        self, 
        file_path: str, 
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """
        Parse a document file.
        
        Args:
            file_path: Path to the document file
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedDocument object with extracted content and metadata
        """
        pass
    
    @abstractmethod
    def parse_stream(
        self, 
        file_stream: BinaryIO,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """
        Parse a document from a file stream.
        
        Args:
            file_stream: File-like object containing the document
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedDocument object with extracted content and metadata
        """
        pass
    
    def is_complex_document(self, content: str) -> bool:
        """
        Determine if a document is complex (requires OCR).
        
        Args:
            content: Document content
            
        Returns:
            True if the document is complex, False otherwise
        """
        # Simple heuristic: if extracted text is very short compared to file size,
        # it might be a scanned document or have embedded images with text
        if len(content) < 100:
            return True
            
        # Check for common indicators of failed text extraction
        indicators = [
            "�",  # Unicode replacement character
            "\ufffd",  # Another form of replacement character
        ]
        
        for indicator in indicators:
            if indicator in content:
                return True
                
        return False
    
    def prepare_metadata(
        self, 
        filename: str, 
        file_size: int,
        user_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare document metadata.
        
        Args:
            filename: Original filename
            file_size: File size in bytes
            user_metadata: Additional user-provided metadata
            
        Returns:
            Document metadata dictionary
        """
        # Extract file extension
        file_extension = os.path.splitext(filename)[1].lower().lstrip(".")
        
        # Base metadata
        metadata = {
            "source_document_id": self.document_id,
            "source_document_name": filename,
            "source_document_type": file_extension,
            "file_size": file_size,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        # Add user metadata if provided
        if user_metadata:
            # Ensure file_path is preserved if it exists in user_metadata
            file_path = user_metadata.get("file_path")
            metadata.update(user_metadata)
            
            # Make sure file_path is included in the metadata
            if file_path:
                metadata["file_path"] = file_path
            
        return metadata