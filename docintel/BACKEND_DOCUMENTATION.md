# DocIntel Backend Documentation

## Overview

DocIntel is a document intelligence system that allows users to upload, search, and chat with documents using RAG (Retrieval-Augmented Generation) capabilities. The backend is built with FastAPI and provides a comprehensive API for managing documents, chatting, and Google Drive integration.

## Project Structure

```
docintel/
├── app/                     # Main application code
│   ├── build/               # Frontend build files (served by the backend)
│   ├── chat/                # Chat-related functionality
│   ├── chunking/            # Document chunking logic
│   ├── drive/               # Google Drive integration
│   ├── embeddings/          # Vector embedding capabilities
│   ├── models/              # Data models
│   ├── parsers/             # Document parsers for different file types
│   ├── rag/                 # Retrieval-Augmented Generation components
│   ├── routes/              # API routes
│   ├── services/            # Service layer
│   ├── storage/             # Storage adapters (ChromaDB)
│   └── utils/               # Utility functions
├── chroma_db/               # ChromaDB vector database files
├── uploads/                 # Uploaded document storage
├── requirements.txt         # Python dependencies
└── Dockerfile               # Docker build configuration
```

## Core Components

### 1. Document Processing Pipeline

Documents undergo several processing steps:
1. **Parsing**: Converting different document formats into text
2. **Chunking**: Breaking text into manageable chunks
3. **Embedding**: Creating vector representations of chunks
4. **Storage**: Storing vectors in ChromaDB for retrieval

### 2. RAG System

The RAG (Retrieval-Augmented Generation) system consists of:
- **Query Optimizer**: Splits complex queries into simpler ones
- **Retriever**: Finds relevant document chunks
- **Generator**: Produces answers based on retrieved content

### 3. Storage

- **ChromaDB**: Vector database for document embeddings
- **File Storage**: Local storage for uploaded documents

## API Endpoints

### Document Management (`/api/documents/`)

| Endpoint | Method | Description | Input | Output |
|----------|--------|-------------|-------|--------|
| `/upload` | POST | Upload and process a document | File, metadata (optional) | Document processing status |
| `/query` | POST | Search across documents | Query text, filter criteria | Relevant document chunks |
| `/list` | GET | List all documents | Page, page size, filters | Paginated document list |
| `/statistics` | GET | Get system statistics | - | Document processing statistics |
| `/{document_id}` | GET | Get document details | Document ID | Document metadata and content |
| `/{document_id}/file` | GET | Download document file | Document ID | Original document file |
| `/{document_id}` | DELETE | Delete a document | Document ID | Deletion status |
| `/{document_id}/highlighted` | GET | Get document with highlighted content | Document ID, chunk ID | Document with highlighted text |

#### Example: Upload Document

```
POST /api/documents/upload
Content-Type: multipart/form-data

file: [binary file data]
metadata: {"created_by": "user123", "tags": ["report", "financial"]}
parallel_processing: true
```

#### Example: Query Documents

```
POST /api/documents/query
Content-Type: application/json

{
  "query": "What is the revenue forecast for Q3?",
  "n_results": 5,
  "filter_criteria": {
    "tags": ["financial"]
  }
}
```

### Chat Sessions (`/api/chat/`)

| Endpoint | Method | Description | Input | Output |
|----------|--------|-------------|-------|--------|
| `/sessions` | POST | Create a chat session | Session title, user ID | New session details |
| `/sessions` | GET | List chat sessions | User ID (optional), pagination | List of chat sessions |
| `/sessions/{session_id}` | GET | Get session details | Session ID | Session details |
| `/sessions/{session_id}` | DELETE | Delete a session | Session ID | Deletion status |
| `/sessions/{session_id}/messages` | GET | Get chat history | Session ID | All messages in the session |
| `/sessions/{session_id}/messages` | POST | Send a message | Message text, RAG options | AI response with citations |
| `/sessions/{session_id}/export` | GET | Export chat session | Session ID | Complete session data |
| `/messages/{message_id}` | GET | Get specific message | Message ID | Message details |
| `/messages/{message_id}/citations` | GET | Get message citations | Message ID | Source citations |
| `/messages/{message_id}/retrieved_chunks` | GET | Get retrieved chunks | Message ID | Document chunks used |
| `/citations/{document_id}/{chunk_id}` | GET | Get citation source | Document ID, chunk ID | Source content |
| `/batch/messages` | POST | Process multiple messages | Messages array, session ID | Multiple AI responses |
| `/sessions/{session_id}/stream/{queue_id}` | GET | Stream processing updates | Session ID, queue ID | SSE stream of updates |
| `/sessions/{session_id}/realtime-stream/{queue_id}` | GET | Real-time streaming | Session ID, queue ID | SSE stream of real-time updates |

#### Example: Create Chat Session

```
POST /api/chat/sessions
Content-Type: application/json

{
  "title": "Financial Report Discussion",
  "user_id": "user123",
  "metadata": {
    "context": "Q3 Financial Report"
  }
}
```

#### Example: Send Message

```
POST /api/chat/sessions/{session_id}/messages
Content-Type: application/json

{
  "text": "Summarize the key findings in the Q3 report",
  "use_rag": true,
  "streaming": true,
  "rag_options": {
    "filter_criteria": {
      "tags": ["financial", "q3"]
    },
    "n_results": 10
  }
}
```

### Google Drive Integration (`/api/drive/`)

| Endpoint | Method | Description | Input | Output |
|----------|--------|-------------|-------|--------|
| `/authorize` | GET | Get authorization URL | Redirect URI | Google OAuth URL |
| `/oauth2callback` | GET | Handle OAuth callback | Code | Access token |
| `/files` | GET | List Drive files | - | List of files |
| `/folders` | GET | List Drive folders | - | List of folders |
| `/import/{file_id}` | POST | Import Drive file | File ID, metadata | Import status |
| `/batch-import` | POST | Import multiple files | File IDs, metadata | Batch import status |

#### Example: Import Drive File

```
POST /api/drive/import/{file_id}
Content-Type: application/json

{
  "metadata": {
    "tags": ["imported", "drive"],
    "created_by": "user123"
  }
}
```

## Data Models

### Document Models

- **DocumentMetadata**: Metadata for document upload
  - `created_by`: User who uploaded the document
  - `tags`: List of tags for categorization
  - `additional_metadata`: Custom metadata

- **DocumentSummary**: Basic document information
  - `document_id`: Unique identifier
  - `filename`: Original filename
  - `document_type`: File type (pdf, docx, etc.)
  - `total_chunks`: Number of chunks
  - `created_at`: Creation timestamp
  - `ocr_used`: Whether OCR was used for text extraction
  - `tags`: List of tags

- **DocumentDetail**: Detailed document information
  - Includes all fields from DocumentSummary
  - `metadata`: Additional metadata
  - `chunks`: Document chunks (optional)

### Chat Models

- **ChatSession**: Represents a conversation
  - `session_id`: Unique identifier
  - `title`: Session title
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp
  - `user_id`: Associated user
  - `metadata`: Additional metadata

- **ChatMessage**: Individual message in a session
  - `message_id`: Unique identifier
  - `session_id`: Parent session ID
  - `text`: Message content
  - `sender`: Who sent the message (user/assistant)
  - `created_at`: Timestamp
  - `citations`: Document references (for assistant responses)
  - `processing_time`: Time taken to generate response
  - `metadata`: Additional metadata

- **Citation**: Reference to document source
  - `citation_id`: Unique identifier
  - `document_id`: Source document
  - `chunk_id`: Specific chunk in document
  - `text`: Cited text
  - `relevance_score`: Relevance to the query

## Authentication

The API does not currently implement authentication. In a production environment, you should add proper authentication and authorization.

## Error Handling

API endpoints return appropriate HTTP status codes:
- `200 OK`: Successful operation
- `201 Created`: Resource successfully created
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include:
```json
{
  "detail": "Error message describing the issue"
}
```

## Concurrent Processing

The backend supports parallel processing of documents and RAG operations:
- `parallel_processing` parameter controls whether operations run in parallel
- Thread pools manage concurrent operations
- Progress tracking for long-running operations

## Running the Application

Start the application with:
```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or using Docker:
```
docker build -t docintel .
docker run -p 8000:8000 docintel
```

## Development Guidelines

1. **Error Handling**: Always provide clear error messages
2. **Documentation**: Keep API documentation up-to-date
3. **Logging**: Use log_step() for important operations
4. **Performance**: Use Timer() to track performance of critical operations
5. **Background Tasks**: Use background_tasks for long-running operations 