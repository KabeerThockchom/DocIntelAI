import re
from typing import List, Dict, Any, Tuple, Optional
import tiktoken
from app.chunking.models import DocumentChunk
from app.utils.logging import log_step, Timer


class DocumentChunker:
    """
    Handles document chunking strategies.
    Implements both heading-based and token-based chunking methods.
    """
    
    def __init__(
        self,
        default_chunk_size: int = 1000,
        default_chunk_overlap: int = 200,
        tokenizer_name: str = "cl100k_base"  # OpenAI's tokenizer
    ):
        self.default_chunk_size = default_chunk_size
        self.default_chunk_overlap = default_chunk_overlap
        self.tokenizer = tiktoken.get_encoding(tokenizer_name)
        
        # Regular expressions for heading detection
        self.heading_patterns = [
            # Markdown headings
            r"^#{1,6}\s+(.+)$",
            # HTML headings
            r"<h[1-6][^>]*>(.+?)</h[1-6]>",
            # Common heading patterns (e.g., "1.2 Section Title")
            r"^(?:\d+\.)+\d*\s+(.+)$",
            # Underlined headings (===== or -----)
            r"^(.+)\n[=\-]{3,}$"
        ]
    
    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any],
        use_headings: bool = True,
        is_ocr: bool = False
    ) -> List[DocumentChunk]:
        """
        Chunk a document using the appropriate strategy.
        
        Args:
            text: Document text to chunk
            metadata: Document metadata
            use_headings: Whether to use heading-based chunking (if available)
            is_ocr: Whether the text is from OCR
            
        Returns:
            List of document chunks
        """
        with Timer("Document Chunking"):
            log_step("Chunking", f"Chunking document {metadata.get('source_document_name', 'unknown')}")
            
            # For OCR text, always use heading-based chunking
            if is_ocr:
                chunks = self._heading_based_chunking(text, metadata)
                if chunks:
                    log_step("Chunking", f"Created {len(chunks)} chunks using heading-based chunking for OCR text")
                    return chunks
                log_step("Chunking", "No clear headings found in OCR text, falling back to token-based chunking")
            
            # Try heading-based chunking first if enabled for non-OCR text
            elif use_headings:
                chunks = self._heading_based_chunking(text, metadata)
                if chunks:
                    log_step("Chunking", f"Created {len(chunks)} chunks using heading-based chunking")
                    return chunks
                log_step("Chunking", "No clear headings found, falling back to token-based chunking")
            
            # Fall back to token-based chunking
            chunks = self._token_based_chunking(text, metadata)
            log_step("Chunking", f"Created {len(chunks)} chunks using token-based chunking")
            return chunks
    
    def _heading_based_chunking(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Chunk a document based on headings.
        
        Args:
            text: Document text to chunk
            metadata: Document metadata
            
        Returns:
            List of document chunks (empty if no headings found)
        """
        # Extract headings and their positions
        headings = []
        text_lines = text.split("\n")
        
        # Check each line for heading patterns
        for i, line in enumerate(text_lines):
            for pattern in self.heading_patterns:
                match = re.search(pattern, line)
                if match:
                    heading_text = match.group(1).strip()
                    heading_level = len(pattern.split(r"#")[0]) if "#" in pattern else 1
                    headings.append({
                        "text": heading_text,
                        "line": i,
                        "level": heading_level
                    })
                    break
        
        # If not enough headings found, return empty list (fallback will be used)
        if len(headings) < 3:  # Need at least 3 headings to use this method
            return []
        
        # Create chunks based on heading sections
        chunks = []
        heading_path = []
        
        for i in range(len(headings)):
            current_heading = headings[i]
            next_heading = headings[i + 1] if i < len(headings) - 1 else None
            
            # Update heading path
            while heading_path and heading_path[-1]["level"] >= current_heading["level"]:
                heading_path.pop()
            heading_path.append(current_heading)
            
            # Extract text between current heading and next heading
            start_line = current_heading["line"]
            end_line = next_heading["line"] if next_heading else len(text_lines)
            
            section_text = "\n".join(text_lines[start_line:end_line])
            
            # Check if section is too large
            tokens = self.tokenizer.encode(section_text)
            if len(tokens) > self.default_chunk_size * 1.5:
                # If section is too large, use token-based chunking for this section
                section_chunks = self._token_based_chunking(section_text, metadata)
                
                # Add heading information to each chunk
                for chunk in section_chunks:
                    chunk.heading_path = [h["text"] for h in heading_path]
                    chunk.heading_level = current_heading["level"]
                
                chunks.extend(section_chunks)
            else:
                # Create a chunk for this section
                chunk = DocumentChunk(
                    text=section_text,
                    metadata=metadata,
                    source_document_id=metadata.get("source_document_id", ""),
                    source_document_name=metadata.get("source_document_name", ""),
                    source_document_type=metadata.get("source_document_type", ""),
                    page_number=metadata.get("page_number"),
                    heading_path=[h["text"] for h in heading_path],
                    heading_level=current_heading["level"],
                    is_ocr=metadata.get("is_ocr", False),
                    created_by=metadata.get("created_by")
                )
                chunks.append(chunk)
        
        return chunks
    
    def _token_based_chunking(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Chunk a document based on token count.
        
        Args:
            text: Document text to chunk
            metadata: Document metadata
            
        Returns:
            List of document chunks
        """
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        # Split text into manageable chunks
        for i in range(0, len(tokens), self.default_chunk_size - self.default_chunk_overlap):
            # Get chunk tokens
            chunk_tokens = tokens[i:i + self.default_chunk_size]
            
            # Convert tokens back to text
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            # Create chunk
            chunk = DocumentChunk(
                text=chunk_text,
                metadata=metadata,
                source_document_id=metadata.get("source_document_id", ""),
                source_document_name=metadata.get("source_document_name", ""),
                source_document_type=metadata.get("source_document_type", ""),
                page_number=metadata.get("page_number"),
                start_index=i,
                end_index=i + len(chunk_tokens),
                is_ocr=metadata.get("is_ocr", False),
                created_by=metadata.get("created_by")
            )
            chunks.append(chunk)
            
            # Stop if we've reached the end of the text
            if i + self.default_chunk_size >= len(tokens):
                break
        
        return chunks