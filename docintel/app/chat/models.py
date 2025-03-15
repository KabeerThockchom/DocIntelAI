from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class ChatSession(BaseModel):
    """Represents a chat session."""
    
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Research on renewable energy",
                "created_at": "2023-11-20T14:30:00",
                "updated_at": "2023-11-20T15:45:00",
                "user_id": "user@example.com",
                "metadata": {
                    "tags": ["research", "energy"]
                }
            }
        }


class Citation(BaseModel):
    """Represents a citation to a document chunk."""
    
    citation_id: str  # The citation marker (e.g., "[1]")
    chunk_id: str
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    bounding_box: Optional[Dict[str, float]] = None
    text_snippet: str
    relevance_score: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "citation_id": "[1]",
                "chunk_id": "chunk123",
                "document_id": "doc123",
                "document_name": "Renewable Energy Report.pdf",
                "page_number": 5,
                "bounding_box": {
                    "x1": 100.5,
                    "y1": 200.3,
                    "x2": 400.2,
                    "y2": 250.1
                },
                "text_snippet": "Solar energy production increased by 25% in the last year...",
                "relevance_score": 0.92
            }
        }


class ChatMessage(BaseModel):
    """Represents a message in a chat session."""
    
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    citations: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "session123",
                "role": "assistant",
                "content": "According to the report [1], solar energy production increased by 25% last year.",
                "created_at": "2023-11-20T14:35:00",
                "citations": [
                    {
                        "citation_id": "[1]",
                        "chunk_id": "chunk123",
                        "document_id": "doc123",
                        "document_name": "Renewable Energy Report.pdf",
                        "page_number": 5,
                        "text_snippet": "Solar energy production increased by 25% in the last year...",
                        "relevance_score": 0.92
                    }
                ],
                "metadata": {
                    "tokens": 42
                }
            }
        }


# Request/Response Models for API
class ChatSessionCreate(BaseModel):
    """Request model for creating a new chat session."""
    
    title: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatSessionResponse(BaseModel):
    """Response model for chat session information."""
    
    session_id: str
    title: str
    created_at: str
    updated_at: str
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SendMessageRequest(BaseModel):
    """
    Request model for sending a message.
    """
    content: str
    metadata: Optional[Dict[str, Any]] = None
    use_retrieval: Optional[bool] = None
    stream_processing: Optional[bool] = False
    include_history: Optional[bool] = True  # Default to including history
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "What were our Q3 financial results?",
                "metadata": {"priority": "high"},
                "use_retrieval": None,  # None means LLM will decide automatically
                "stream_processing": True,
                "include_history": True
            }
        }


class MessageResponse(BaseModel):
    """Response model for a chat message."""
    
    message_id: str
    session_id: str
    role: str
    content: str
    created_at: str
    citations: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatSessionListResponse(BaseModel):
    """Response model for listing chat sessions."""
    
    sessions: List[ChatSessionResponse]
    total_count: int


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    
    session_id: str
    title: str
    messages: List[MessageResponse]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CitationDetails(BaseModel):
    """Response model for detailed citation information."""
    
    citation: Citation
    document_metadata: Dict[str, Any]
    context: str  # Surrounding context for the citation