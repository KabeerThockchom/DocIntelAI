# Parsers Package
"""
Document parsers for different file types (PDF, DOCX, Excel, PPTX).
"""

from app.parsers.base_parser import BaseDocumentParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DocxParser
from app.parsers.excel_parser import ExcelParser
from app.parsers.pptx_parser import PPTXParser
from app.parsers.ocr import OCRProcessor

# Factory function to get appropriate parser based on file extension
def get_parser(file_extension: str):
    """
    Get appropriate parser for a file type.
    
    Args:
        file_extension: File extension (pdf, docx, xlsx, pptx, etc.)
        
    Returns:
        Appropriate parser instance
    """
    file_extension = file_extension.lower().lstrip(".")
    
    if file_extension == "pdf":
        return PDFParser()
    elif file_extension == "docx":
        return DocxParser()
    elif file_extension in ["xlsx", "xls", "csv"]:
        return ExcelParser()
    elif file_extension == "pptx":
        return PPTXParser()
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")