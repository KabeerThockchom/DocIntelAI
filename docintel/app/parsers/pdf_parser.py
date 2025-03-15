import os
import time
from typing import Dict, List, Any, Optional, BinaryIO, Tuple
import fitz  # PyMuPDF
from io import BytesIO

from app.parsers.base_parser import BaseDocumentParser
from app.parsers.ocr import OCRProcessor
from app.chunking.models import ProcessedDocument
from app.chunking.chunker import DocumentChunker
from app.utils.logging import log_step, Timer


class PDFParser(BaseDocumentParser):
    """Parser for PDF documents."""
    
    def __init__(self, chunker: Optional[DocumentChunker] = None):
        """
        Initialize PDF parser.
        
        Args:
            chunker: Document chunker instance (optional)
        """
        super().__init__()
        self.chunker = chunker or DocumentChunker()
        self.ocr_processor = OCRProcessor()
    
    def parse(
        self, 
        file_path: str, 
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """
        Parse a PDF file.
        
        Args:
            file_path: Path to the PDF file
            filename: Original filename (uses basename of file_path if not provided)
            metadata: Additional metadata
            
        Returns:
            ProcessedDocument object with extracted content and metadata
        """
        with Timer("PDF Parsing"):
            # Get filename if not provided
            if not filename:
                filename = os.path.basename(file_path)
                
            log_step("PDF Parsing", f"Parsing PDF file: {filename}")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Prepare metadata
            doc_metadata = self.prepare_metadata(filename, file_size, metadata)
            
            # Start timer for processing
            start_time = time.time()
            
            try:
                # Try simple PDF parsing first
                text_by_page, is_complex = self._extract_text_from_pdf(file_path)
                
                # If simple parsing failed or detected a complex document, use OCR
                if is_complex:
                    log_step("PDF Parsing", "Complex PDF detected, using OCR")
                    ocr_results = self.ocr_processor.process_file(file_path, "pdf")
                    
                    # Convert OCR results to text by page format
                    text_by_page = {}
                    if ocr_results:
                        text_by_page = {
                            result["page_number"]: {
                                "text": result["text"],
                                "is_ocr": True
                            }
                            for result in ocr_results
                            if result and result.get("text")
                        }
                    
                    # If OCR failed to extract any text, try one more time with higher quality
                    if not text_by_page:
                        log_step("PDF Parsing", "OCR failed, retrying with higher quality settings", level="warning")
                        self.ocr_processor = OCRProcessor(max_workers=2)  # Reduce workers but increase quality
                        ocr_results = self.ocr_processor.process_file(file_path, "pdf")
                        if ocr_results:
                            text_by_page = {
                                result["page_number"]: {
                                    "text": result["text"],
                                    "is_ocr": True
                                }
                                for result in ocr_results
                                if result and result.get("text")
                            }
                
                # No text extracted
                if not text_by_page:
                    log_step("PDF Parsing", "No text extracted from PDF", level="warning")
                    return ProcessedDocument(
                        document_id=self.document_id,
                        filename=filename,
                        file_type="pdf",
                        file_size=file_size,
                        total_pages=0,
                        total_chunks=0,
                        chunks=[],
                        processing_time=time.time() - start_time,
                        is_complex=is_complex
                    )
                
                # Process each page
                all_chunks = []
                
                for page_num, page_data in text_by_page.items():
                    page_text = page_data["text"]
                    is_ocr = page_data.get("is_ocr", False)
                    
                    # Skip empty pages
                    if not page_text:
                        continue
                    
                    # Add page number to metadata
                    page_metadata = doc_metadata.copy()
                    page_metadata["page_number"] = page_num
                    page_metadata["is_ocr"] = is_ocr
                    
                    # Chunk the page
                    page_chunks = self.chunker.chunk_document(
                        page_text,
                        page_metadata,
                        use_headings=True,
                        is_ocr=is_ocr
                    )
                    
                    all_chunks.extend(page_chunks)
                
                # Calculate total number of pages
                total_pages = max(text_by_page.keys()) if text_by_page else 0
                
                # Create processed document
                processed_doc = ProcessedDocument(
                    document_id=self.document_id,
                    filename=filename,
                    file_type="pdf",
                    file_size=file_size,
                    total_pages=total_pages,
                    total_chunks=len(all_chunks),
                    chunks=all_chunks,
                    processing_time=time.time() - start_time,
                    is_complex=is_complex
                )
                
                log_step("PDF Parsing", f"Completed parsing PDF with {total_pages} pages and {len(all_chunks)} chunks")
                return processed_doc
                
            except Exception as e:
                log_step("PDF Parsing", f"Error parsing PDF: {str(e)}", level="error")
                raise
    
    def parse_stream(
        self, 
        file_stream: BinaryIO,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """
        Parse a PDF from a file stream.
        
        Args:
            file_stream: File-like object containing the PDF
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedDocument object with extracted content and metadata
        """
        with Timer("PDF Stream Parsing"):
            log_step("PDF Parsing", f"Parsing PDF from stream: {filename}")
            
            # Get file size
            file_stream.seek(0, os.SEEK_END)
            file_size = file_stream.tell()
            file_stream.seek(0)
            
            # Prepare metadata
            doc_metadata = self.prepare_metadata(filename, file_size, metadata)
            
            # Start timer for processing
            start_time = time.time()
            
            try:
                # Create in-memory file
                pdf_data = file_stream.read()
                memory_stream = BytesIO(pdf_data)
                
                # Try simple PDF parsing first
                text_by_page, is_complex = self._extract_text_from_pdf_stream(memory_stream)
                
                # If simple parsing failed or detected a complex document, use OCR
                if is_complex:
                    log_step("PDF Parsing", "Complex PDF detected, using OCR")
                    # Reset file stream
                    file_stream.seek(0)
                    ocr_results = self.ocr_processor.process_stream(file_stream, "pdf", filename)
                    
                    # Convert OCR results to text by page format
                    text_by_page = {}
                    if ocr_results:
                        text_by_page = {
                            result["page_number"]: {
                                "text": result["text"],
                                "is_ocr": True
                            }
                            for result in ocr_results
                            if result and result.get("text")
                        }
                    
                    # If OCR failed to extract any text, try one more time with higher quality
                    if not text_by_page:
                        log_step("PDF Parsing", "OCR failed, retrying with higher quality settings", level="warning")
                        self.ocr_processor = OCRProcessor(max_workers=2)  # Reduce workers but increase quality
                        ocr_results = self.ocr_processor.process_stream(file_stream, "pdf", filename)
                        if ocr_results:
                            text_by_page = {
                                result["page_number"]: {
                                    "text": result["text"],
                                    "is_ocr": True
                                }
                                for result in ocr_results
                                if result and result.get("text")
                            }
                
                # No text extracted
                if not text_by_page:
                    log_step("PDF Parsing", "No text extracted from PDF", level="warning")
                    return ProcessedDocument(
                        document_id=self.document_id,
                        filename=filename,
                        file_type="pdf",
                        file_size=file_size,
                        total_pages=0,
                        total_chunks=0,
                        chunks=[],
                        processing_time=time.time() - start_time,
                        is_complex=is_complex
                    )
                
                # Process each page
                all_chunks = []
                
                for page_num, page_data in text_by_page.items():
                    page_text = page_data["text"]
                    is_ocr = page_data.get("is_ocr", False)
                    
                    # Skip empty pages
                    if not page_text:
                        continue
                    
                    # Add page number to metadata
                    page_metadata = doc_metadata.copy()
                    page_metadata["page_number"] = page_num
                    page_metadata["is_ocr"] = is_ocr
                    
                    # Chunk the page
                    page_chunks = self.chunker.chunk_document(
                        page_text,
                        page_metadata,
                        use_headings=True,
                        is_ocr=is_ocr
                    )
                    
                    all_chunks.extend(page_chunks)
                
                # Calculate total number of pages
                total_pages = max(text_by_page.keys()) if text_by_page else 0
                
                # Create processed document
                processed_doc = ProcessedDocument(
                    document_id=self.document_id,
                    filename=filename,
                    file_type="pdf",
                    file_size=file_size,
                    total_pages=total_pages,
                    total_chunks=len(all_chunks),
                    chunks=all_chunks,
                    processing_time=time.time() - start_time,
                    is_complex=is_complex
                )
                
                log_step("PDF Parsing", f"Completed parsing PDF with {total_pages} pages and {len(all_chunks)} chunks")
                return processed_doc
                
            except Exception as e:
                log_step("PDF Parsing", f"Error parsing PDF stream: {str(e)}", level="error")
                raise
    
    def _extract_text_from_pdf(self, file_path: str) -> Tuple[Dict[int, Dict[str, Any]], bool]:
        """
        Extract text from PDF using PyMuPDF.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (text by page dictionary, is complex document flag)
        """
        text_by_page = {}
        is_complex = False
        
        try:
            pdf = fitz.open(file_path)
            
            # Extract text from each page
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                text = page.get_text()
                
                # Check if page is complex (needs OCR)
                if not text or len(text) < 50:
                    is_complex = True
                
                text_by_page[page_num + 1] = {
                    "text": text,
                    "is_ocr": False
                }
            
            # If overall text extraction is poor, flag as complex
            if len(pdf) > 0:
                avg_text_len = sum(len(page_data["text"]) for page_data in text_by_page.values()) / len(pdf)
                if avg_text_len < 100:
                    is_complex = True
            
            return text_by_page, is_complex
            
        except Exception as e:
            log_step("PDF Parsing", f"Error in simple PDF parsing: {str(e)}", level="warning")
            return {}, True
    
    def _extract_text_from_pdf_stream(self, memory_stream: BytesIO) -> Tuple[Dict[int, Dict[str, Any]], bool]:
        """
        Extract text from PDF stream using PyMuPDF.
        
        Args:
            memory_stream: BytesIO object containing the PDF
            
        Returns:
            Tuple of (text by page dictionary, is complex document flag)
        """
        text_by_page = {}
        is_complex = False
        
        try:
            # Reset stream position
            memory_stream.seek(0)
            
            pdf = fitz.open(stream=memory_stream, filetype="pdf")
            
            # Extract text from each page
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                text = page.get_text()
                
                # Check if page is complex (needs OCR)
                if not text or len(text) < 50:
                    is_complex = True
                
                text_by_page[page_num + 1] = {
                    "text": text,
                    "is_ocr": False
                }
            
            # If overall text extraction is poor, flag as complex
            if len(pdf) > 0:
                avg_text_len = sum(len(page_data["text"]) for page_data in text_by_page.values()) / len(pdf)
                if avg_text_len < 100:
                    is_complex = True
            
            return text_by_page, is_complex
            
        except Exception as e:
            log_step("PDF Parsing", f"Error in simple PDF parsing from stream: {str(e)}", level="warning")
            return {}, True