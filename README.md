# DocIntel

A powerful document intelligence platform that enables document uploading, processing, embedding, and semantic search with AI-powered chat capabilities.

[Watch Demo Video](https://youtu.be/VimZ6YngrFI)

## Features

- **Document Processing:** Upload and process PDF, DOCX, PPTX, Excel files
- **Intelligent Chunking:** Smart document chunking for optimal retrieval
- **Vector Embeddings:** Generate and store embeddings for semantic search
- **AI-Powered Chat:** Chat with your documents using AI
- **Citation Support:** Get citations with source document context
- **Multi-User Support:** Document collections separated by user
- **Parallel Processing:** Efficient document processing with parallel embedding generation
- **OCR Capabilities:** Extract text from scanned documents and images

## Technology Stack

- **Backend:** FastAPI
- **Vector Database:** Qdrant
- **Embeddings:** Azure OpenAI
- **Containerization:** Docker
- **Deployment:** Fly.io

## Installation

### Prerequisites

- Python 3.8+
- Docker (optional)

### Local Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/docintel.git
   cd docintel
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   uvicorn app.main:app --reload
   ```

### Docker Setup

1. Build the Docker image:
   ```
   docker build -t docintel .
   ```

2. Run the container:
   ```
   docker run -p 8000:8000 docintel
   ```

## Usage

### Uploading Documents

Upload documents using the `/upload` endpoint. Supported file types include:
- PDF (.pdf)
- Word Documents (.docx)
- PowerPoint Presentations (.pptx)
- Excel Spreadsheets (.xlsx, .xls, .csv)

### Querying Documents

Use the `/query` endpoint to search through processed documents with natural language queries.

### Chat with Documents

Create a chat session with the `/sessions` endpoint and send messages to interact with your documents.

## API Endpoints

### Document Management

- `POST /upload` - Upload and process a document
- `GET /list` - List all documents
- `GET /{document_id}` - Get document details
- `DELETE /{document_id}` - Delete a document
- `GET /{document_id}/file` - Download original document
- `GET /statistics` - Get document statistics

### Chat

- `POST /sessions` - Create a new chat session
- `GET /sessions` - List chat sessions
- `GET /sessions/{session_id}` - Get chat session details
- `DELETE /sessions/{session_id}` - Delete a chat session
- `GET /sessions/{session_id}/messages` - Get chat history
- `POST /sessions/{session_id}/messages` - Send a message
- `GET /messages/{message_id}` - Get a specific message
- `GET /messages/{message_id}/citations` - Get citations for a message
- `GET /citations/{document_id}/{chunk_id}` - Get citation source

## Architecture

DocIntel uses a modular architecture:

1. **Parser Module** - Extracts text and metadata from different document types
2. **Chunking Module** - Divides documents into manageable chunks for processing
3. **Embedding Module** - Generates vector embeddings for document chunks
4. **Storage Module** - Manages vector storage using Qdrant
5. **Chat Module** - Handles chat sessions and message processing

## Deployment

DocIntel can be deployed to Fly.io using the included `fly.toml` configuration:

```
fly launch
```

## License

[MIT License](LICENSE)
