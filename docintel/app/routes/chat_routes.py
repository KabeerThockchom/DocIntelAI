import os
import json
import asyncio
import queue
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from openai import AzureOpenAI
import httpx

from app.chat.models import (
    ChatSessionCreate, ChatSessionResponse, SendMessageRequest, 
    MessageResponse, ChatSessionListResponse, ChatHistoryResponse,
    ChatSession, ChatMessage, Citation
)
from app.rag.query_optimizer import optimize_query, split_query_into_subqueries
from app.rag.retriever import retrieve_relevant_chunks, retrieve_relevant_chunks_async, retrieve_relevant_chunks_for_multiple_queries
from app.rag.generator import generate_answer, generate_answer_async, batch_generate_answers
from app.rag.groq_retrieval_decider import should_use_retrieval
from app.storage.chroma_db import ChromaDBStorage
from app.utils.logging import log_step, Timer

router = APIRouter()

# Initialize components
chroma_db = ChromaDBStorage()

# Initialize Azure OpenAI client with custom http_client to avoid proxies issue
http_client = httpx.Client()
azure_openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_API_VERSION", "2024-02-15-preview"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
    http_client=http_client
)

# Configure thread pool for parallel processing
# Using a thread pool with a reasonable number of workers
# based on the high API limits (20,000 requests per minute)
MAX_WORKERS = 10
thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Mock database for chat sessions and messages
# In a production environment, this would be replaced with a real database
chat_sessions = {}
chat_messages = {}

# Queue for processing updates
session_queues = {}

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(session_data: ChatSessionCreate):
    """
    Create a new chat session.
    
    Args:
        session_data: Session creation data
    
    Returns:
        Created chat session
    """
    with Timer("Create Chat Session"):
        session_id = str(uuid.uuid4())
        created_at = datetime.now()
        
        # Create session
        session = ChatSession(
            session_id=session_id,
            title=session_data.title,
            created_at=created_at,
            updated_at=created_at,
            user_id=session_data.user_id,
            metadata=session_data.metadata or {}
        )
        
        # Store in mock database
        chat_sessions[session_id] = session
        
        # Convert to response model
        return ChatSessionResponse(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            user_id=session.user_id,
            metadata=session.metadata
        )

@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    user_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50)
):
    """
    List chat sessions, optionally filtered by user_id.
    
    Args:
        user_id: Optional user ID filter
        skip: Number of sessions to skip
        limit: Maximum number of sessions to return
    
    Returns:
        List of chat sessions
    """
    with Timer("List Chat Sessions"):
        # Filter sessions
        if user_id:
            filtered_sessions = [
                session for session in chat_sessions.values() 
                if session.user_id == user_id
            ]
        else:
            filtered_sessions = list(chat_sessions.values())
        
        # Sort by updated_at (newest first)
        filtered_sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        # Apply pagination
        paginated_sessions = filtered_sessions[skip:skip + limit]
        
        # Convert to response model
        session_responses = [
            ChatSessionResponse(
                session_id=session.session_id,
                title=session.title,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                user_id=session.user_id,
                metadata=session.metadata
            )
            for session in paginated_sessions
        ]
        
        return ChatSessionListResponse(
            sessions=session_responses,
            total_count=len(filtered_sessions)
        )

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(session_id: str = Path(..., description="Chat session ID")):
    """
    Get a chat session by ID.
    
    Args:
        session_id: Chat session ID
    
    Returns:
        Chat session details
    """
    with Timer("Get Chat Session"):
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        return ChatSessionResponse(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            user_id=session.user_id,
            metadata=session.metadata
        )

@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str = Path(..., description="Chat session ID")):
    """
    Delete a chat session and its messages.
    
    Args:
        session_id: Chat session ID
    
    Returns:
        Deletion status
    """
    with Timer("Delete Chat Session"):
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Delete session
        del chat_sessions[session_id]
        
        # Delete messages for this session
        session_messages = [
            msg_id for msg_id, msg in chat_messages.items() 
            if msg.session_id == session_id
        ]
        
        for msg_id in session_messages:
            del chat_messages[msg_id]
        
        return {"status": "success", "message": f"Chat session {session_id} deleted"}

@router.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str = Path(..., description="Chat session ID")
):
    """
    Get the message history for a chat session.
    
    Args:
        session_id: Chat session ID
    
    Returns:
        Chat history
    """
    with Timer("Get Chat History"):
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        # Get messages for this session
        session_messages = [
            msg for msg in chat_messages.values() 
            if msg.session_id == session_id
        ]
        
        # Sort by creation time
        session_messages.sort(key=lambda msg: msg.created_at)
        
        # Convert to response model
        message_responses = [
            MessageResponse(
                message_id=msg.message_id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat(),
                citations=msg.citations,
                metadata=msg.metadata
            )
            for msg in session_messages
        ]
        
        return ChatHistoryResponse(
            session_id=session.session_id,
            title=session.title,
            messages=message_responses,
            metadata=session.metadata
        )

async def get_chat_history_for_context(session_id: str):
    """
    Get the chat history for a session to use as context in processing.
    
    Args:
        session_id: Chat session ID
        
    Returns:
        List of messages in the chat history formatted as dicts with role and content
    """
    if session_id not in chat_sessions:
        return []
    
    # Get messages for this session
    session_messages = [
        msg for msg in chat_messages.values() 
        if msg.session_id == session_id
    ]
    
    # Sort by creation time
    session_messages.sort(key=lambda msg: msg.created_at)
    
    # Format messages as dicts with role and content for LLM context
    formatted_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in session_messages
    ]
    
    return formatted_messages

async def save_message(message_data):
    """
    Save a message to the chat history.
    
    Args:
        message_data: Message data to save
    
    Returns:
        Saved message
    """
    message_id = message_data["message_id"]
    
    # Create message object
    message = ChatMessage(
        message_id=message_id,
        session_id=message_data["session_id"],
        role=message_data["role"],
        content=message_data["content"],
        created_at=datetime.fromisoformat(message_data["created_at"]) if isinstance(message_data["created_at"], str) else message_data["created_at"],
        citations=message_data.get("citations", []),
        metadata=message_data.get("metadata", {})
    )
    
    # Store in mock database
    chat_messages[message_id] = message
    
    return message

async def update_session_activity(session_id):
    """
    Update the last activity timestamp for a chat session.
    
    Args:
        session_id: Chat session ID
    
    Returns:
        Updated session
    """
    if session_id in chat_sessions:
        session = chat_sessions[session_id]
        session.updated_at = datetime.now()
        return session
    return None

@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    message: SendMessageRequest,
    parallel_processing: bool = Query(True, description="Whether to use parallel processing"),
    response: Response = None
):
    """
    Send a message to a chat session and get an AI response.
    
    Args:
        session_id: Chat session ID
        message: Message content and metadata
        parallel_processing: Whether to use parallel processing for RAG
        response: FastAPI response object for setting headers
        
    Returns:
        Message response with AI-generated content
    """
    try:
        # Validate session exists
        session = await get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Get chat history
        chat_history = await get_chat_history_for_context(session_id)
        
        # Create user message
        user_message = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "user",
            "content": message.content,
            "created_at": datetime.now().isoformat(),
            "citations": [],
            "metadata": message.metadata or {}
        }
        
        # Save user message
        await save_message(user_message)
        
        # Update session last activity
        await update_session_activity(session_id)
        
        # Determine if retrieval should be used
        use_retrieval = message.use_retrieval
        
        # Create a queue for this request if streaming is enabled
        queue_id = f"{session_id}_{str(uuid.uuid4())}"
        if message.stream_processing:
            session_queues[queue_id] = queue.Queue()
            # Send initial processing update
            session_queues[queue_id].put({
                "type": "processing_update",
                "stage": "analyzing_query",
                "message": "Analyzing your question...",
                "queue_id": queue_id
            })
            
            # Set the queue_id in the response headers
            if response:
                response.headers["X-Queue-ID"] = queue_id
        
        # If use_retrieval is not explicitly set to False, let the LLM decide
        if use_retrieval is not False:
            # Pass chat history to the retrieval decision function if include_history is True
            history_for_decision = chat_history if message.include_history else []
            retrieval_decision = should_use_retrieval(message.content, history_for_decision)
            use_retrieval = retrieval_decision.get("retrieval_needed", True)
            retrieval_reasoning = retrieval_decision.get("reasoning", "")
            
            # Send retrieval decision update
            if message.stream_processing and queue_id in session_queues:
                session_queues[queue_id].put({
                    "type": "processing_update",
                    "stage": "deciding_retrieval",
                    "message": f"Decision: {retrieval_reasoning}",
                    "details": {"retrievalNeeded": use_retrieval}
                })
        else:
            retrieval_reasoning = "User explicitly disabled retrieval"
            
            # Send retrieval decision update
            if message.stream_processing and queue_id in session_queues:
                session_queues[queue_id].put({
                    "type": "processing_update",
                    "stage": "deciding_retrieval",
                    "message": "Retrieval disabled by user",
                    "details": {"retrievalNeeded": False}
                })
        
        # Generate AI response
        if use_retrieval:
            if parallel_processing:
                # Parallel processing for RAG
                # Split query into sub-queries and run retrieval in parallel
                loop = asyncio.get_event_loop()
                
                # Run query splitting in a thread
                # Pass chat history to the query splitting function if include_history is True
                history_for_splitting = chat_history if message.include_history else []
                split_task = loop.run_in_executor(
                    thread_pool,
                    lambda: split_query_into_subqueries(message.content, history_for_splitting)
                )
                
                # Wait for splitting to complete
                sub_queries = await split_task
                
                # Log the number of sub-queries for debugging
                log_step("RAG", f"Split query into {len(sub_queries)} sub-queries: {', '.join(sub_queries[:3])}" + ("..." if len(sub_queries) > 3 else ""))
                
                # Send query splitting update
                if message.stream_processing and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "splitting_query",
                        "message": f"Breaking down your question into {len(sub_queries)} sub-queries",
                        "details": {
                            "isComplex": True,
                            "subQueries": sub_queries,
                            "originalQuery": message.content
                        }
                    })
                
                # Retrieve chunks for all sub-queries asynchronously
                retrieved_chunks = await retrieve_relevant_chunks_for_multiple_queries(
                    queries=sub_queries,
                    top_k=10
                )
                
                # Send retrieval update
                if message.stream_processing and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "retrieving_documents",
                        "message": f"Found {len(retrieved_chunks)} relevant chunks from your documents",
                        "details": {
                            "chunkCount": len(retrieved_chunks)
                        }
                    })
                
                # Send generation update
                if message.stream_processing and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "generating_answer",
                        "message": "Generating a comprehensive answer...",
                        "details": {}
                    })
                
                # Generate answer asynchronously
                # Pass chat history to the answer generation function if include_history is True
                history_for_generation = chat_history if message.include_history else []
                result = await generate_answer_async(
                    query=message.content,
                    retrieved_chunks=retrieved_chunks,
                    chat_history=history_for_generation
                )
                
                # Extract answer and citations
                ai_content = result["answer"]
                citations = result["citations"]
                
                # Send completion update
                if message.stream_processing and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "complete",
                        "message": "Answer ready!",
                        "details": {}
                    })
            else:
                # Sequential processing for RAG
                # Split query into sub-queries
                # Pass chat history to the query splitting function if include_history is True
                history_for_splitting = chat_history if message.include_history else []
                sub_queries = split_query_into_subqueries(message.content, history_for_splitting)
                
                # Log the number of sub-queries for debugging
                log_step("RAG", f"Split query into {len(sub_queries)} sub-queries: {', '.join(sub_queries[:3])}" + ("..." if len(sub_queries) > 3 else ""))
                
                # Retrieve chunks for each sub-query and merge results
                all_chunks = []
                seen_chunk_ids = set()
                
                for query in sub_queries:
                    chunks = retrieve_relevant_chunks(query, top_k=10)
                    for chunk in chunks:
                        chunk_id = chunk["chunk_id"]
                        if chunk_id not in seen_chunk_ids:
                            seen_chunk_ids.add(chunk_id)
                            all_chunks.append(chunk)
                
                # Limit to top 20 chunks (increased from 10 to ensure coverage for multiple topics)
                retrieved_chunks = all_chunks[:20]
                
                # Send retrieval update
                if message.stream_processing and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "retrieving_documents",
                        "message": f"Found {len(retrieved_chunks)} relevant chunks from your documents",
                        "details": {
                            "chunkCount": len(retrieved_chunks)
                        }
                    })
                
                # Send generation update
                if message.stream_processing and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "generating_answer",
                        "message": "Generating a comprehensive answer...",
                        "details": {}
                    })
                
                # Generate answer
                # Pass chat history to the answer generation function if include_history is True
                history_for_generation = chat_history if message.include_history else []
                result = generate_answer(
                    query=message.content,
                    retrieved_chunks=retrieved_chunks,
                    chat_history=history_for_generation
                )
                
                # Extract answer and citations
                ai_content = result["answer"]
                citations = result["citations"]
                
                # Send completion update
                if message.stream_processing and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "complete",
                        "message": "Answer ready!",
                        "details": {}
                    })
        else:
            # No retrieval needed, generate answer without context
            # Send generation update
            if message.stream_processing and queue_id in session_queues:
                session_queues[queue_id].put({
                    "type": "processing_update",
                    "stage": "generating_answer",
                    "message": "Generating a direct answer...",
                    "details": {}
                })
            
            # Generate a simple response without retrieval
            # Use a simpler prompt for direct questions
            system_prompt = {
                "role": "system",
                "content": (
                    "You are an intelligent assistant that provides helpful, accurate, and concise responses. "
                    "Format your responses using Markdown for better readability. "
                    "If you don't know the answer to a question, simply state that you don't have that information."
                )
            }
            
            # Create messages array
            messages = [system_prompt]
            
            # Add chat history if include_history is True
            if message.include_history:
                # Format chat history
                for msg in chat_history:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Add user's question
            messages.append({
                "role": "user",
                "content": message.content
            })
            
            # Call Azure OpenAI
            response = azure_openai_client.chat.completions.create(
                model=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract the response
            ai_content = response.choices[0].message.content.strip()
            citations = []  # No citations for direct answers
            
            # Send completion update
            if message.stream_processing and queue_id in session_queues:
                session_queues[queue_id].put({
                    "type": "processing_update",
                    "stage": "complete",
                    "message": "Answer ready!",
                    "details": {}
                })
        
        # Include all retrieved chunks as sources, not just the cited ones
        all_sources = []
        seen_chunk_ids = set()
        
        # First add the cited chunks
        for citation in citations:
            seen_chunk_ids.add(citation["chunk_id"])
            all_sources.append(citation)
        
        # Then add the non-cited chunks as additional sources
        for chunk in retrieved_chunks if use_retrieval else []:
            chunk_id = chunk["chunk_id"]
            if chunk_id not in seen_chunk_ids:
                # Create a citation object for the non-cited chunk
                source = {
                    "citation_id": str(uuid.uuid4()),
                    "chunk_id": chunk_id,
                    "document_id": chunk["metadata"]["source_document_id"],
                    "document_name": chunk["metadata"]["source_document_name"],
                    "page_number": chunk["metadata"]["page_number"] if chunk["metadata"]["page_number"] != -1 else None,
                    "text_snippet": chunk["text"],
                    "relevance_score": 0.0,  # Not cited, so no relevance score
                    "is_cited": False  # Mark as not directly cited
                }
                seen_chunk_ids.add(chunk_id)
                all_sources.append(source)
        
        # Create assistant message with all sources
        assistant_message = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "assistant",
            "content": ai_content,
            "created_at": datetime.now().isoformat(),
            "citations": all_sources if use_retrieval else [],
            "metadata": {
                "retrieval_used": use_retrieval,
                "retrieval_reasoning": retrieval_reasoning,
                "include_history": message.include_history
            }
        }
        
        # Save assistant message
        await save_message(assistant_message)
        
        # Update session last activity
        await update_session_activity(session_id)
        
        return assistant_message
        
    except Exception as e:
        log_step("Chat", f"Error processing message: {str(e)}", level="error")
        
        # Send error update
        if message.stream_processing and queue_id in session_queues:
            session_queues[queue_id].put({
                "type": "processing_update",
                "stage": "complete",
                "message": f"Error: {str(e)}",
                "details": {"error": True}
            })
            
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@router.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(message_id: str = Path(..., description="Message ID")):
    """
    Get a specific message by ID.
    
    Args:
        message_id: Message ID
    
    Returns:
        Message details
    """
    with Timer("Get Message"):
        if message_id not in chat_messages:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message = chat_messages[message_id]
        
        return MessageResponse(
            message_id=message.message_id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at.isoformat(),
            citations=message.citations,
            metadata=message.metadata
        )

@router.get("/messages/{message_id}/citations")
async def get_message_citations(message_id: str = Path(..., description="Message ID")):
    """
    Get citations for a specific message.
    
    Args:
        message_id: Message ID
    
    Returns:
        List of citations
    """
    with Timer("Get Message Citations"):
        if message_id not in chat_messages:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message = chat_messages[message_id]
        
        return {"citations": message.citations}

@router.get("/citations/{document_id}/{chunk_id}")
async def get_citation_source(
    document_id: str = Path(..., description="Document ID"),
    chunk_id: str = Path(..., description="Chunk ID")
):
    """
    Get the source information for a citation.
    
    Args:
        document_id: Document ID
        chunk_id: Chunk ID
    
    Returns:
        Source information with context
    """
    with Timer("Get Citation Source"):
        # Get document details
        document = chroma_db.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get chunk details
        chunks = chroma_db.get_document_chunks(document_id)
        
        # Find the specific chunk
        chunk = next((c for c in chunks if c["chunk_id"] == chunk_id), None)
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Get surrounding context (adjacent chunks)
        context_chunks = []
        for c in chunks:
            # Check if chunk is in the same page/section
            same_page = (
                c["metadata"].get("page_number") == chunk["metadata"].get("page_number")
                if "page_number" in chunk["metadata"]
                else False
            )
            
            if same_page:
                context_chunks.append(c)
        
        # Sort context chunks by position
        context_chunks.sort(key=lambda c: c["metadata"].get("start_index", 0))
        
        # Format source information
        return {
            "document": {
                "document_id": document_id,
                "filename": document.get("filename", "Unknown"),
                "document_type": document.get("document_type", "Unknown"),
                "page_number": chunk["metadata"].get("page_number"),
                "bounding_box": chunk["metadata"].get("bounding_box")
            },
            "chunk": {
                "chunk_id": chunk_id,
                "text": chunk["text"],
                "metadata": chunk["metadata"]
            },
            "context": {
                "chunks": context_chunks[:5],  # Limit to 5 chunks for context
                "total_chunks": len(context_chunks)
            }
        }

@router.get("/sessions/{session_id}/export")
async def export_chat_session(
    session_id: str = Path(..., description="Chat session ID"),
    include_citations: bool = Query(True, description="Include detailed citation information")
):
    """
    Export a chat session with all messages and citations.
    
    Args:
        session_id: Chat session ID
        include_citations: Whether to include detailed citation information
    
    Returns:
        Complete chat export
    """
    with Timer("Export Chat Session"):
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        # Get messages for this session
        session_messages = [
            msg for msg in chat_messages.values() 
            if msg.session_id == session_id
        ]
        
        # Sort by creation time
        session_messages.sort(key=lambda msg: msg.created_at)
        
        # Format messages for export
        formatted_messages = []
        for msg in session_messages:
            message_data = {
                "message_id": msg.message_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "metadata": msg.metadata
            }
            
            if include_citations and msg.citations:
                message_data["citations"] = msg.citations
            
            formatted_messages.append(message_data)
        
        return {
            "session": {
                "session_id": session.session_id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "user_id": session.user_id,
                "metadata": session.metadata
            },
            "messages": formatted_messages,
            "export_time": datetime.now().isoformat()
        }

# Add a new endpoint for batch processing multiple messages
@router.post("/batch/messages", response_model=List[MessageResponse])
async def batch_process_messages(
    messages: List[SendMessageRequest],
    session_id: str = Query(..., description="Chat session ID")
):
    """
    Process multiple messages in parallel for a chat session.
    
    Args:
        messages: List of messages to process
        session_id: Chat session ID
    
    Returns:
        List of AI response messages
    """
    with Timer(f"Batch Process {len(messages)} Messages"):
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Update session
        session = chat_sessions[session_id]
        session.updated_at = datetime.now()
        
        # Get chat history for context
        history_messages = [
            msg for msg in chat_messages.values() 
            if msg.session_id == session_id
        ]
        
        # Sort by creation time
        history_messages.sort(key=lambda msg: msg.created_at)
        
        # Format chat history for RAG
        chat_history = [
            {"role": msg.role, "content": msg.content} 
            for msg in history_messages[-5:]  # Use last 5 messages
        ]
        
        # Process all messages in parallel
        user_message_ids = []
        user_messages = []
        
        # Create user messages
        for message in messages:
            user_message_id = str(uuid.uuid4())
            user_message_ids.append(user_message_id)
            
            user_message = ChatMessage(
                message_id=user_message_id,
                session_id=session_id,
                role="user",
                content=message.content,
                created_at=datetime.now(),
                citations=[],
                metadata=message.metadata or {}
            )
            
            # Save user message
            chat_messages[user_message_id] = user_message
            user_messages.append(user_message)
        
        # Process queries in parallel
        queries = [msg.content for msg in messages]
        
        # Optimize queries in parallel
        loop = asyncio.get_event_loop()
        optimize_tasks = [
            loop.run_in_executor(
                thread_pool,
                lambda q=query: optimize_query(q, chat_history)
            )
            for query in queries
        ]
        optimized_queries = await asyncio.gather(*optimize_tasks)
        
        # Retrieve chunks for all queries in parallel
        retrieval_tasks = [
            retrieve_relevant_chunks_async(query)
            for query in optimized_queries
        ]
        all_retrieved_chunks = await asyncio.gather(*retrieval_tasks)
        
        # Generate answers for all queries in parallel
        results = await batch_generate_answers(
            queries=queries,
            retrieved_chunks_list=all_retrieved_chunks,
            chat_histories=[chat_history] * len(queries)
        )
        
        # Create assistant messages
        ai_messages = []
        ai_message_responses = []
        
        for i, result in enumerate(results):
            ai_message_id = str(uuid.uuid4())
            
            ai_message = ChatMessage(
                message_id=ai_message_id,
                session_id=session_id,
                role="assistant",
                content=result["answer"],
                created_at=datetime.now(),
                citations=result["citations"],
                metadata={
                    "generated_with_retrieval": True,
                    "parallel_processing": True,
                    "batch_processed": True
                }
            )
            
            # Save assistant message
            chat_messages[ai_message_id] = ai_message
            ai_messages.append(ai_message)
            
            # Convert to response model
            ai_message_response = MessageResponse(
                message_id=ai_message.message_id,
                session_id=ai_message.session_id,
                role=ai_message.role,
                content=ai_message.content,
                created_at=ai_message.created_at.isoformat(),
                citations=ai_message.citations,
                metadata=ai_message.metadata
            )
            ai_message_responses.append(ai_message_response)
        
        return ai_message_responses

@router.get("/sessions/{session_id}/stream/{queue_id}")
async def stream_processing_updates(
    request: Request,
    session_id: str,
    queue_id: str
):
    """
    Stream processing updates using Server-Sent Events (SSE).
    
    Args:
        request: FastAPI request
        session_id: Chat session ID
        queue_id: Queue ID for this specific request
        
    Returns:
        SSE streaming response
    """
    if queue_id not in session_queues:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    return StreamingResponse(
        stream_events(queue_id),
        media_type="text/event-stream"
    )

def stream_events(queue_id: str):
    """
    Generator function for SSE streaming.
    
    Args:
        queue_id: Queue ID for this specific request
        
    Yields:
        SSE formatted events
    """
    if queue_id not in session_queues:
        return
    
    q = session_queues[queue_id]
    
    try:
        while True:
            try:
                data = q.get(timeout=30)  # 30 second timeout
                yield f"data: {json.dumps(data)}\n\n"
            except queue.Empty:
                # Send keepalive
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
    except GeneratorExit:
        # Clean up when client disconnects
        if queue_id in session_queues:
            del session_queues[queue_id]