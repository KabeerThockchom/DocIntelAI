# DocIntel API Routes Documentation

This document provides detailed information about all API routes available in the DocIntel system.

## Table of Contents

- [Document Management Routes](#document-management-routes)
- [Chat Session Routes](#chat-session-routes)
- [Google Drive Integration Routes](#google-drive-integration-routes)

## Document Management Routes

Base path: `/api/documents`

### Upload Document

```
POST /api/documents/upload
```

Uploads and processes a document file.

**Parameters:**
- `file` (required): The document file to upload
- `metadata` (optional): JSON string with document metadata
- `parallel_processing` (optional, default: true): Whether to use parallel processing

**Request Example:**
```
POST /api/documents/upload HTTP/1.1
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="file"; filename="financial_report.pdf"
Content-Type: application/pdf

[Binary PDF data]
--boundary
Content-Disposition: form-data; name="metadata"

{"created_by": "user123", "tags": ["financial", "quarterly"]}
--boundary
Content-Disposition: form-data; name="parallel_processing"

true
--boundary--
```

**Response:**
```json
{
  "status": "processing",
  "filename": "financial_report.pdf",
  "parallel_processing": true
}
```

### Query Documents

```
POST /api/documents/query
```

Searches for relevant document chunks based on a query.

**Request Body:**
- `query` (string, required): The search query text
- `n_results` (integer, optional, default: 5): Number of results to return
- `filter_criteria` (object, optional): Filters to apply to search results

**Request Example:**
```json
{
  "query": "What is the revenue forecast for Q3?",
  "n_results": 10,
  "filter_criteria": {
    "tags": ["financial"],
    "document_type": "pdf"
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "chunk_id_1",
      "document_id": "doc_id_1",
      "text": "The revenue forecast for Q3 2023 is projected to be $5.2M, representing a 12% increase year-over-year.",
      "metadata": {
        "source_document_name": "Q3_Forecast.pdf",
        "page_number": 4,
        "tags": ["financial"]
      },
      "distance": 0.12
    },
    ...
  ]
}
```

### List Documents

```
GET /api/documents/list
```

Lists documents in the system with pagination.

**Query Parameters:**
- `document_type` (string, optional): Filter by document type
- `page` (integer, optional, default: 1): Page number
- `page_size` (integer, optional, default: 10, max: 100): Number of documents per page

**Response:**
```json
{
  "documents": [
    {
      "document_id": "doc_id_1",
      "filename": "financial_report.pdf",
      "document_type": "pdf",
      "total_chunks": 45,
      "created_at": "2023-06-15T09:12:34Z",
      "ocr_used": false,
      "tags": ["financial", "quarterly"]
    },
    ...
  ],
  "pagination": {
    "total": 125,
    "page": 1,
    "page_size": 10,
    "total_pages": 13
  }
}
```

### Get System Statistics

```
GET /api/documents/statistics
```

Returns system-wide document statistics.

**Response:**
```json
{
  "total_documents": 125,
  "document_types": {
    "pdf": 78,
    "docx": 32,
    "pptx": 10,
    "xlsx": 5
  },
  "total_chunks": 4325,
  "total_ocr_chunks": 157,
  "ocr_percentage": 3.63,
  "avg_chunks_per_document": 34.6
}
```

### Get Document Details

```
GET /api/documents/{document_id}
```

Returns detailed information about a specific document.

**Path Parameters:**
- `document_id` (string, required): Document ID

**Query Parameters:**
- `include_chunks` (boolean, optional, default: false): Whether to include document chunks

**Response:**
```json
{
  "document_id": "doc_id_1",
  "filename": "financial_report.pdf",
  "document_type": "pdf",
  "total_chunks": 45,
  "created_at": "2023-06-15T09:12:34Z",
  "ocr_used": false,
  "tags": ["financial", "quarterly"],
  "metadata": {
    "created_by": "user123",
    "file_path": "/uploads/user123/20230615_091234_financial_report.pdf",
    "page_count": 12
  },
  "chunks": [
    {
      "chunk_id": "chunk_id_1",
      "text": "Executive Summary: Q3 Financial Performance",
      "metadata": {
        "page_number": 1
      }
    },
    ...
  ]
}
```

### Download Document File

```
GET /api/documents/{document_id}/file
```

Downloads the original document file.

**Path Parameters:**
- `document_id` (string, required): Document ID

**Query Parameters:**
- `page` (integer, optional): Page number to navigate to (for PDF files)

**Response:**
The original document file with appropriate content type and headers.

### Delete Document

```
DELETE /api/documents/{document_id}
```

Deletes a document and all its chunks.

**Path Parameters:**
- `document_id` (string, required): Document ID

**Response:**
```json
{
  "status": "success",
  "message": "Document doc_id_1 deleted"
}
```

### Get Highlighted Document

```
GET /api/documents/{document_id}/highlighted
```

Gets the original document with a specific chunk highlighted.

**Path Parameters:**
- `document_id` (string, required): Document ID

**Query Parameters:**
- `chunk_id` (string, required): Chunk ID to highlight

**Response:**
The original document file with the specified chunk highlighted.

## Chat Session Routes

Base path: `/api/chat`

### Create Chat Session

```
POST /api/chat/sessions
```

Creates a new chat session.

**Request Body:**
- `title` (string, required): Session title
- `user_id` (string, optional): User ID
- `metadata` (object, optional): Additional metadata

**Request Example:**
```json
{
  "title": "Q3 Financial Analysis",
  "user_id": "user123",
  "metadata": {
    "project": "quarterly_review"
  }
}
```

**Response:**
```json
{
  "session_id": "session_id_1",
  "title": "Q3 Financial Analysis",
  "created_at": "2023-06-15T10:23:45Z",
  "updated_at": "2023-06-15T10:23:45Z",
  "user_id": "user123",
  "metadata": {
    "project": "quarterly_review"
  }
}
```

### List Chat Sessions

```
GET /api/chat/sessions
```

Lists all chat sessions with optional filtering.

**Query Parameters:**
- `user_id` (string, optional): Filter by user ID
- `skip` (integer, optional, default: 0): Number of sessions to skip
- `limit` (integer, optional, default: 10, max: 50): Maximum number of sessions to return

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_id_1",
      "title": "Q3 Financial Analysis",
      "created_at": "2023-06-15T10:23:45Z",
      "updated_at": "2023-06-15T11:45:12Z",
      "user_id": "user123",
      "metadata": {
        "project": "quarterly_review"
      }
    },
    ...
  ],
  "total_count": 23
}
```

### Get Chat Session

```
GET /api/chat/sessions/{session_id}
```

Gets details of a specific chat session.

**Path Parameters:**
- `session_id` (string, required): Session ID

**Response:**
```json
{
  "session_id": "session_id_1",
  "title": "Q3 Financial Analysis",
  "created_at": "2023-06-15T10:23:45Z",
  "updated_at": "2023-06-15T11:45:12Z",
  "user_id": "user123",
  "metadata": {
    "project": "quarterly_review"
  }
}
```

### Delete Chat Session

```
DELETE /api/chat/sessions/{session_id}
```

Deletes a chat session and all its messages.

**Path Parameters:**
- `session_id` (string, required): Session ID

**Response:**
```json
{
  "status": "success",
  "message": "Session session_id_1 deleted"
}
```

### Get Chat History

```
GET /api/chat/sessions/{session_id}/messages
```

Gets the message history for a chat session.

**Path Parameters:**
- `session_id` (string, required): Session ID

**Response:**
```json
{
  "session_id": "session_id_1",
  "title": "Q3 Financial Analysis",
  "messages": [
    {
      "message_id": "msg_id_1",
      "session_id": "session_id_1",
      "text": "What were the key revenue drivers in Q3?",
      "sender": "user",
      "created_at": "2023-06-15T10:24:15Z",
      "metadata": {}
    },
    {
      "message_id": "msg_id_2",
      "session_id": "session_id_1",
      "text": "The key revenue drivers in Q3 were product line A (+15%) and service B (+22%). These were partially offset by a decline in product line C (-5%).",
      "sender": "assistant",
      "created_at": "2023-06-15T10:24:18Z",
      "citations": [
        {
          "citation_id": "citation_id_1",
          "document_id": "doc_id_1",
          "chunk_id": "chunk_id_3",
          "text": "Product line A saw 15% growth in Q3, while service offering B experienced 22% growth year-over-year.",
          "relevance_score": 0.92
        },
        ...
      ],
      "processing_time": 2.34,
      "metadata": {
        "tokens_used": 128
      }
    },
    ...
  ]
}
```

### Send Message

```
POST /api/chat/sessions/{session_id}/messages
```

Sends a message to a chat session and gets a response.

**Path Parameters:**
- `session_id` (string, required): Session ID

**Query Parameters:**
- `parallel_processing` (boolean, optional, default: true): Whether to use parallel processing

**Request Body:**
- `text` (string, required): Message text
- `use_rag` (boolean, optional, default: true): Whether to use RAG for response generation
- `streaming` (boolean, optional, default: false): Whether to stream the response
- `rag_options` (object, optional): Options for RAG
  - `filter_criteria` (object, optional): Filters for document retrieval
  - `n_results` (integer, optional, default: 10): Number of chunks to retrieve

**Request Example:**
```json
{
  "text": "What were the key revenue drivers in Q3?",
  "use_rag": true,
  "streaming": true,
  "rag_options": {
    "filter_criteria": {
      "tags": ["financial", "quarterly"]
    },
    "n_results": 15
  }
}
```

**Response:**
```json
{
  "message_id": "msg_id_2",
  "session_id": "session_id_1",
  "text": "The key revenue drivers in Q3 were product line A (+15%) and service B (+22%). These were partially offset by a decline in product line C (-5%).",
  "sender": "assistant",
  "created_at": "2023-06-15T10:24:18Z",
  "citations": [
    {
      "citation_id": "citation_id_1",
      "document_id": "doc_id_1",
      "chunk_id": "chunk_id_3",
      "text": "Product line A saw 15% growth in Q3, while service offering B experienced 22% growth year-over-year.",
      "relevance_score": 0.92
    },
    ...
  ],
  "processing_time": 2.34,
  "metadata": {
    "tokens_used": 128,
    "queue_id": "queue_id_1",  // Only present if streaming is true
    "retrieved_chunks": [
      {
        "chunk_id": "chunk_id_3",
        "document_id": "doc_id_1",
        "text": "Product line A saw 15% growth in Q3, while service offering B experienced 22% growth year-over-year.",
        "metadata": {
          "page_number": 4
        }
      },
      ...
    ]
  }
}
```

### Get Message Details

```
GET /api/chat/messages/{message_id}
```

Gets details of a specific message.

**Path Parameters:**
- `message_id` (string, required): Message ID

**Response:**
```json
{
  "message_id": "msg_id_2",
  "session_id": "session_id_1",
  "text": "The key revenue drivers in Q3 were product line A (+15%) and service B (+22%). These were partially offset by a decline in product line C (-5%).",
  "sender": "assistant",
  "created_at": "2023-06-15T10:24:18Z",
  "citations": [
    {
      "citation_id": "citation_id_1",
      "document_id": "doc_id_1",
      "chunk_id": "chunk_id_3",
      "text": "Product line A saw 15% growth in Q3, while service offering B experienced 22% growth year-over-year.",
      "relevance_score": 0.92
    },
    ...
  ],
  "processing_time": 2.34,
  "metadata": {
    "tokens_used": 128
  }
}
```

### Get Message Citations

```
GET /api/chat/messages/{message_id}/citations
```

Gets citations for a specific message.

**Path Parameters:**
- `message_id` (string, required): Message ID

**Response:**
```json
{
  "citations": [
    {
      "citation_id": "citation_id_1",
      "document_id": "doc_id_1",
      "chunk_id": "chunk_id_3",
      "text": "Product line A saw 15% growth in Q3, while service offering B experienced 22% growth year-over-year.",
      "relevance_score": 0.92,
      "document_metadata": {
        "filename": "financial_report.pdf",
        "document_type": "pdf",
        "page_number": 4
      }
    },
    ...
  ]
}
```

### Get Retrieved Chunks

```
GET /api/chat/messages/{message_id}/retrieved_chunks
```

Gets the document chunks retrieved for a specific message.

**Path Parameters:**
- `message_id` (string, required): Message ID

**Response:**
```json
{
  "retrieved_chunks": [
    {
      "chunk_id": "chunk_id_3",
      "document_id": "doc_id_1",
      "text": "Product line A saw 15% growth in Q3, while service offering B experienced 22% growth year-over-year.",
      "metadata": {
        "source_document_name": "financial_report.pdf",
        "page_number": 4
      },
      "distance": 0.08
    },
    ...
  ]
}
```

### Get Citation Source

```
GET /api/chat/citations/{document_id}/{chunk_id}
```

Gets the source content for a citation.

**Path Parameters:**
- `document_id` (string, required): Document ID
- `chunk_id` (string, required): Chunk ID

**Response:**
```json
{
  "document_id": "doc_id_1",
  "chunk_id": "chunk_id_3",
  "text": "Product line A saw 15% growth in Q3, while service offering B experienced 22% growth year-over-year.",
  "document_metadata": {
    "filename": "financial_report.pdf",
    "document_type": "pdf",
    "created_at": "2023-06-15T09:12:34Z"
  },
  "chunk_metadata": {
    "page_number": 4,
    "section": "Financial Results"
  }
}
```

### Export Chat Session

```
GET /api/chat/sessions/{session_id}/export
```

Exports a complete chat session.

**Path Parameters:**
- `session_id` (string, required): Session ID

**Query Parameters:**
- `include_citations` (boolean, optional, default: true): Whether to include detailed citation information

**Response:**
```json
{
  "session_id": "session_id_1",
  "title": "Q3 Financial Analysis",
  "created_at": "2023-06-15T10:23:45Z",
  "updated_at": "2023-06-15T11:45:12Z",
  "user_id": "user123",
  "metadata": {
    "project": "quarterly_review"
  },
  "messages": [
    {
      "message_id": "msg_id_1",
      "text": "What were the key revenue drivers in Q3?",
      "sender": "user",
      "created_at": "2023-06-15T10:24:15Z"
    },
    {
      "message_id": "msg_id_2",
      "text": "The key revenue drivers in Q3 were product line A (+15%) and service B (+22%). These were partially offset by a decline in product line C (-5%).",
      "sender": "assistant",
      "created_at": "2023-06-15T10:24:18Z",
      "citations": [
        {
          "citation_id": "citation_id_1",
          "document_id": "doc_id_1",
          "chunk_id": "chunk_id_3",
          "text": "Product line A saw 15% growth in Q3, while service offering B experienced 22% growth year-over-year.",
          "relevance_score": 0.92,
          "document_metadata": {
            "filename": "financial_report.pdf"
          }
        },
        ...
      ]
    },
    ...
  ]
}
```

### Batch Process Messages

```
POST /api/chat/batch/messages
```

Processes multiple messages in batch.

**Query Parameters:**
- `session_id` (string, required): Chat session ID

**Request Body:**
- Array of message objects, each containing:
  - `text` (string, required): Message text
  - `use_rag` (boolean, optional, default: true): Whether to use RAG
  - `rag_options` (object, optional): Options for RAG

**Request Example:**
```json
{
  "messages": [
    {
      "text": "What were the key revenue drivers in Q3?",
      "use_rag": true,
      "rag_options": {
        "filter_criteria": {
          "tags": ["financial"]
        }
      }
    },
    {
      "text": "How did expenses compare to budget?",
      "use_rag": true
    }
  ]
}
```

**Response:**
Array of message response objects.

### Stream Processing Updates

```
GET /api/chat/sessions/{session_id}/stream/{queue_id}
```

Streams processing updates for a message.

**Path Parameters:**
- `session_id` (string, required): Session ID
- `queue_id` (string, required): Queue ID returned from send message call

**Response:**
Server-sent events (SSE) stream with processing updates.

Example events:
```
event: update
data: {"stage": "retrieving", "message": "Retrieving relevant documents", "details": {"progress": 30}, "is_completed": false}

event: update
data: {"stage": "generating", "message": "Generating response", "details": {"progress": 50}, "is_completed": false}

event: complete
data: {"stage": "complete", "message": "Processing complete", "details": {}, "is_completed": true}
```

### Realtime Stream Updates

```
GET /api/chat/sessions/{session_id}/realtime-stream/{queue_id}
```

Streams real-time updates including partial message generation.

**Path Parameters:**
- `session_id` (string, required): Session ID
- `queue_id` (string, required): Queue ID returned from send message call

**Response:**
Server-sent events (SSE) stream with real-time updates.

Example events:
```
event: update
data: {"stage": "retrieving", "message": "Retrieving relevant documents", "details": {"progress": 30}, "is_completed": false}

event: token
data: {"token": "The", "index": 0}

event: token
data: {"token": " key", "index": 1}

event: token
data: {"token": " revenue", "index": 2}

...

event: complete
data: {"stage": "complete", "message": "Processing complete", "details": {}, "is_completed": true}
```

## Google Drive Integration Routes

Base path: `/api/drive`

### Get Authorization URL

```
GET /api/drive/auth-url
```

Gets the Google OAuth authorization URL.

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=..."
}
```

### Authenticate

```
POST /api/drive/auth
```

Authenticates with Google using an authorization code.

**Request Body:**
- `code` (string, required): Authorization code from Google OAuth

**Request Example:**
```json
{
  "code": "4/P7q7W91a-oMsCeLvIaQm6bTrgtp7"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Authentication successful"
}
```

### List Files

```
GET /api/drive/files
```

Lists files in Google Drive.

**Query Parameters:**
- `folder_id` (string, optional): Folder ID to list files from (root folder if omitted)
- `file_types` (string, optional): Comma-separated list of file extensions to filter by

**Response:**
```json
{
  "files": [
    {
      "id": "file_id_1",
      "name": "Q3 Financial Report.pdf",
      "mimeType": "application/pdf",
      "size": "2048000",
      "createdTime": "2023-06-01T09:12:34Z",
      "modifiedTime": "2023-06-02T14:23:45Z"
    },
    ...
  ]
}
```

### Process Drive File

```
POST /api/drive/process-file
```

Processes a single file from Google Drive.

**Request Body:**
- `file_id` (string, required): Google Drive file ID
- `metadata` (object, optional): Additional metadata

**Request Example:**
```json
{
  "file_id": "file_id_1",
  "metadata": {
    "tags": ["financial", "quarterly"],
    "created_by": "user123"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "file_id": "file_id_1",
  "document_id": "doc_id_1",
  "filename": "Q3 Financial Report.pdf"
}
```

### Process Multiple Files

```
POST /api/drive/process-files
```

Processes multiple files from Google Drive.

**Request Body:**
- `file_ids` (array of strings, required): List of Google Drive file IDs
- `metadata` (object, optional): Additional metadata

**Request Example:**
```json
{
  "file_ids": ["file_id_1", "file_id_2", "file_id_3"],
  "metadata": {
    "tags": ["financial", "quarterly"],
    "created_by": "user123"
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "status": "success",
      "file_id": "file_id_1",
      "document_id": "doc_id_1",
      "filename": "Q3 Financial Report.pdf"
    },
    {
      "status": "success",
      "file_id": "file_id_2",
      "document_id": "doc_id_2",
      "filename": "Q3 Marketing Report.docx"
    },
    {
      "status": "error",
      "file_id": "file_id_3",
      "error": "Unsupported file type"
    }
  ]
}
```

### Process Folder

```
POST /api/drive/process-folder
```

Processes all files in a Google Drive folder.

**Request Body:**
- `folder_id` (string, required): Google Drive folder ID
- `file_types` (array of strings, optional): File types to process
- `metadata` (object, optional): Additional metadata

**Request Example:**
```json
{
  "folder_id": "folder_id_1",
  "file_types": ["pdf", "docx", "pptx"],
  "metadata": {
    "tags": ["financial", "quarterly"],
    "created_by": "user123"
  }
}
```

**Response:**
```json
{
  "status": "processing",
  "folder_id": "folder_id_1"
}
``` 