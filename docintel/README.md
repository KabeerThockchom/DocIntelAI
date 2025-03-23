# Inkling

A comprehensive document processing system that parses, chunks, embeds, and retrieves content from various document types. The system supports PDF, DOCX, PPTX, and Excel/CSV files, with intelligent OCR capabilities for complex documents.

## Features

- **Document Parsing**: Extract text from multiple file formats
  - PDF parsing with PyMuPDF
  - DOCX parsing with python-docx
  - PPTX parsing with python-pptx
  - Excel/CSV parsing with pandas and openpyxl
  - OCR for complex documents using Azure OpenAI GPT-4o-mini

- **Intelligent Chunking**:
  - Smart heading-based chunking
  - Fallback chunking of 1000 tokens with 200-token overlap

- **Embedding Generation**:
  - Semantic embeddings using Azure OpenAI's text-ada-002 model

- **Google Drive Integration**:
  - Connect to Google Drive to import documents
  - Process individual files or entire folders

- **Vector Storage**:
  - Local Chroma DB for storing embeddings and chunks
  - Efficient retrieval with semantic search

- **Bulk Processing**:
  - Parallel processing of multiple documents
  - Background task execution

## System Requirements

- Python 3.8+
- FastAPI
- PyMuPDF, python-docx, python-pptx, pandas, openpyxl
- Azure OpenAI API access
- Chroma DB
- Google API credentials (for Google Drive integration)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/document-processor.git
   cd document-processor
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   # Azure OpenAI API
   export AZURE_OPENAI_API_KEY=your_api_key
   export AZURE_API_VERSION=2024-02-15-preview
   export ENDPOINT_URL=https://your-endpoint.openai.azure.com/
   export DEPLOYMENT_NAME=gpt-4o-mini
   
   # Google Drive API (optional)
   export GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
   ```

## Usage

1. Start the FastAPI server:
   ```
   uvicorn app.main:app --reload
   ```

2. Access the API documentation:
   ```
   http://localhost:8000/docs
   ```

### API Endpoints

#### Document Processing

- `POST /api/documents/upload`: Upload and process a document
- `POST /api/documents/query`: Query processed documents
- `DELETE /api/documents/{document_id}`: Delete a document

#### Google Drive Integration

- `GET /api/drive/auth-url`: Get Google Drive authentication URL
- `POST /api/drive/auth`: Authenticate with Google Drive
- `GET /api/drive/files`: List files in Google Drive
- `POST /api/drive/process-file`: Process a file from Google Drive
- `POST /api/drive/process-folder`: Process a folder from Google Drive

## Project Structure

```
document_processor/
├── app/
│   ├── __init__.py
│   ├── main.py (FastAPI application entry point)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── document_routes.py (API endpoints for document processing)
│   │   └── drive_routes.py (API endpoints for Google Drive integration)
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py (Base parser class)
│   │   ├── pdf_parser.py (PDF parsing implementation)
│   │   ├── docx_parser.py (DOCX parsing implementation)
│   │   ├── excel_parser.py (Excel parsing implementation)
│   │   ├── pptx_parser.py (PPTX parsing implementation)
│   │   └── ocr.py (OCR for complex files)
│   ├── chunking/
│   │   ├── __init__.py
│   │   ├── chunker.py (Chunking strategies implementation)
│   │   └── models.py (Document chunk models)
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── embedder.py (Embedding generation implementation)
│   ├── storage/
│   │   ├── __init__.py
│   │   └── chroma_db.py (Chroma DB integration)
│   ├── drive/
│   │   ├── __init__.py
│   │   └── google_drive.py (Google Drive integration)
│   └── utils/
│       ├── __init__.py
│       └── logging.py (Logging utilities)
├── requirements.txt
└── README.md
```

## Implementation Details

### Document Parsing

The system uses a cascading approach to document parsing:

1. First, it attempts to extract text using native parsers (PyMuPDF, python-docx, etc.)
2. If the extraction yields poor results or no text, it falls back to OCR using Azure OpenAI's GPT-4o-mini
3. The system automatically detects complex documents that require OCR

### Chunking Strategy

Documents are chunked using two strategies:

1. **Heading-based chunking**: The system tries to identify headings in the document and chunks content based on logical sections
2. **Token-based chunking**: If heading-based chunking is not possible, the system falls back to chunking based on token count (1000 tokens with 200 overlap)

### Embedding and Storage

1. Each chunk is embedded using Azure OpenAI's text-ada-002 model
2. Embeddings and chunk metadata are stored in a local Chroma DB
3. The system preserves rich metadata including source information, page numbers, and heading paths

### Google Drive Integration

1. Users can authenticate with Google Drive using OAuth
2. The system supports processing individual files or entire folders
3. Files are automatically downloaded, processed, and stored in the vector database

## Future Improvements

1. Implement a user interface for document management and query
2. Add support for more file types
3. Implement document versioning and change tracking
4. Enhance chunking strategies with more advanced techniques
5. Add collaborative features for team environments
6. Integrate with LMS platforms (Canvas, Moodle, etc.)

## License

MIT License

## Acknowledgements

- OpenAI and Azure for the embedding and OCR models
- The Chroma DB team for the vector database
- The developers of PyMuPDF, python-docx, python-pptx, and other libraries used in this project