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
import sys
import logging
import traceback
import time

from app.chat.models import (
    ChatSessionCreate, ChatSessionResponse, SendMessageRequest, 
    MessageResponse, ChatSessionListResponse, ChatHistoryResponse,
    ChatSession, ChatMessage, Citation
)
from app.rag.query_optimizer import split_query_into_subqueries
from app.rag.retriever import retrieve_relevant_chunks, retrieve_relevant_chunks_async, retrieve_relevant_chunks_for_multiple_queries
from app.rag.generator import generate_answer, generate_answer_async, batch_generate_answers
from app.rag.groq_retrieval_decider import should_use_retrieval
from app.storage.qdrant_db import QdrantDBStorage
from app.utils.logging import log_step, Timer

router = APIRouter()

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

# Helper function to get Qdrant storage for the current user
def get_user_storage(request: Request):
    """Get Qdrant storage for the current user."""
    user_id = getattr(request.state, "user_id", None)
    return QdrantDBStorage(user_id=user_id)

# Debug function to count active queues
def count_active_queues():
    return len(session_queues)

@router.get("/debug/queues")
async def debug_queues():
    """Debug endpoint to check active queues"""
    active_queues = list(session_queues.keys())
    return {
        "active_queue_count": len(active_queues),
        "active_queues": active_queues
    }

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
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50)
):
    """
    List chat sessions for the current user.
    
    Args:
        request: Request object with user ID in state
        skip: Number of sessions to skip
        limit: Maximum number of sessions to return
    
    Returns:
        List of chat sessions for the current user
    """
    with Timer("List Chat Sessions"):
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            logging.warning("User ID not found in request state when listing chat sessions")
            return ChatSessionListResponse(sessions=[], total_count=0)
            
        # Filter sessions by user_id
        filtered_sessions = [
            session for session in chat_sessions.values() 
            if session.user_id == user_id
        ]
        
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
async def get_chat_session(
    request: Request,
    session_id: str = Path(..., description="Chat session ID")
):
    """
    Get a chat session by ID.
    
    Args:
        request: Request object with user ID in state
        session_id: Chat session ID
    
    Returns:
        Chat session details if owned by the current user
    """
    with Timer("Get Chat Session"):
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        # Verify that the session belongs to the current user
        if user_id and session.user_id != user_id:
            logging.warning(f"User {user_id} attempted to access session {session_id} owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to access this chat session")
        
        return ChatSessionResponse(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            user_id=session.user_id,
            metadata=session.metadata
        )

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    request: Request,
    session_id: str = Path(..., description="Chat session ID")
):
    """
    Delete a chat session and its messages.
    
    Args:
        request: Request object with user ID in state
        session_id: Chat session ID
    
    Returns:
        Deletion status
    """
    with Timer("Delete Chat Session"):
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        # Verify that the session belongs to the current user
        if user_id and session.user_id != user_id:
            logging.warning(f"User {user_id} attempted to delete session {session_id} owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to delete this chat session")
        
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
    request: Request,
    session_id: str = Path(..., description="Chat session ID")
):
    """
    Get the chat history for a session.
    
    Args:
        request: Request object with user ID in state
        session_id: Chat session ID
        
    Returns:
        Chat history with messages if the session is owned by the current user
    """
    # Get user ID from request state
    user_id = getattr(request.state, "user_id", None)
    
    try:
        # Start timing for logging
        start_time = time.time()
        logging.info("[Get Chat History] Started")
        
        # Validate session exists
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        # Verify that the session belongs to the current user
        if user_id and session.user_id and session.user_id != user_id:
            logging.warning(f"User {user_id} attempted to access chat history for session {session_id} owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to access this chat history")
        
        # Get all messages for this session from chat_messages
        session_messages_list = [msg for msg in chat_messages.values() if msg.session_id == session_id]
        
        # Sort messages by creation time
        session_messages_list.sort(key=lambda msg: msg.created_at)
        
        # Convert messages to response format
        formatted_messages = [
            MessageResponse(
                message_id=msg.message_id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat(),
                citations=msg.citations,
                metadata=msg.metadata
            )
            for msg in session_messages_list
        ]
        
        # Log processing time for diagnostics
        logging.info(f"[Get Chat History] Completed in {time.time() - start_time:.1f}")
        
        # Return chat history response
        return ChatHistoryResponse(
            session_id=session_id,
            title=session.title,
            messages=formatted_messages,
            metadata=session.metadata
        )
    except Exception as e:
        logging.error(f"Error getting chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")

async def get_chat_history_for_context(session_id: str, user_id: Optional[str] = None):
    """
    Get the chat history for a session to use as context for the AI.
    
    Args:
        session_id: Chat session ID
        user_id: Optional user ID for authentication
        
    Returns:
        List of chat messages formatted as dictionaries with role and content
    """
    # Access the global session_messages dictionary
    global chat_messages, chat_sessions
    
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    session = chat_sessions[session_id]
    
    # Verify that the session belongs to the current user
    if user_id and session.user_id and session.user_id != user_id:
        logging.warning(f"User {user_id} attempted to access chat history for session {session_id} owned by {session.user_id}")
        raise HTTPException(status_code=403, detail="You don't have permission to access this chat history")
    
    # Get messages for this session
    session_messages = [msg for msg in chat_messages.values() if msg.session_id == session_id]
    
    # Sort messages by creation time
    sorted_messages = sorted(session_messages, key=lambda m: m.created_at)
    
    # Convert ChatMessage objects to dictionaries with role and content
    formatted_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in sorted_messages
    ]
    
    logging.info(f"Retrieved {len(formatted_messages)} messages for chat context in session {session_id}")
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

def send_realtime_update(queue, stage, message, details=None, is_completed=False):
    """
    Send a processing update with priority for real-time streaming.
    This variation ensures updates are sent immediately without batching.
    
    Args:
        queue: The queue to send updates to
        stage: The current processing stage
        message: The update message
        details: Optional details to include
        is_completed: Whether this stage is completed
    """
    if not queue:
        logging.error(f"Cannot send update for stage {stage}: Queue is None")
        return
    
    # Calculate progress percentage based on stage and completion status
    stages = ["analyzing_query", "deciding_retrieval", "splitting_query", 
              "retrieving_documents", "generating_answer", "complete"]
    
    # Find position in stages list
    try:
        stage_idx = stages.index(stage)
        # Calculate progress: each stage is 20% (5 stages)
        if stage == "complete":
            progress_percentage = 100
        elif is_completed:
            # If the stage is complete, give it full weight
            progress_percentage = min(100, (stage_idx + 1) * 20)
        else:
            # If the stage is in progress, give it half weight
            progress_percentage = min(100, stage_idx * 20 + 10)
    except ValueError:
        # Default to 0% if stage not found
        progress_percentage = 0
        logging.warning(f"Unknown stage in send_realtime_update: {stage}")
    
    # Extract step information from details if available
    steps = None
    current_step = None
    completed_steps = None
    
    if details:
        steps = details.get("steps")
        current_step = details.get("current_step")
        completed_steps = details.get("completed_steps")
    
    # Create the update payload
    update = {
        "type": "processing_update",
        "stage": stage,
        "message": message,
        "details": details or {},
        "isCompleted": is_completed,  # Explicitly set completion status
        "progressPercentage": progress_percentage,
        "steps": steps,  # Add steps information if available
        "current_step": current_step,  # Current step being executed
        "completed_steps": completed_steps,  # Steps that have been completed
        "sent_at": time.time()  # Add timestamp for debugging
    }
    
    # Put the update in the queue - use non-blocking to prevent processing delays
    try:
        queue.put_nowait(update)  # Use put_nowait to avoid blocking
        logging.info(f"Sent real-time update: {stage} - {message} - isCompleted: {is_completed}")
    except Exception as e:
        logging.error(f"Failed to send update to queue: {str(e)}")
        if isinstance(e, queue.Full):
            logging.warning(f"Queue full, dropping update: {stage} - {message}")
        else:
            logging.error(f"Unknown error sending to queue: {type(e).__name__} - {str(e)}")

@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    request: Request,
    session_id: str,
    message: SendMessageRequest,
    parallel_processing: bool = Query(True, description="Whether to use parallel processing"),
    response: Response = None
):
    """
    Send a message to a chat session and get an AI response.
    
    Args:
        request: Request object with user ID in state
        session_id: Chat session ID
        message: Message content and metadata
        parallel_processing: Whether to use parallel processing for RAG
        response: FastAPI response object for setting headers
        
    Returns:
        Message response with AI-generated content if the session is owned by the current user
    """
    try:
        # Ensure we have a response object to set headers
        if response is None:
            response = Response()
            logging.warning("Response object was None in send_message, created new Response")
        
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        
        # Validate session exists
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        # Verify that the session belongs to the current user
        if user_id and session.user_id != user_id:
            logging.warning(f"User {user_id} attempted to send message to session {session_id} owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to send messages to this chat session")
        
        # Get chat history for context with user verification
        chat_history = await get_chat_history_for_context(session_id, user_id)
        
        # Verify chat history format
        if chat_history:
            log_step("Chat", f"Retrieved {len(chat_history)} messages for chat context")
            for i, msg in enumerate(chat_history):
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    log_step("Chat", f"Chat history message {i} has invalid format, fixing", level="warning")
                    # Try to fix the format if possible
                    if isinstance(msg, dict):
                        if "role" not in msg and "user_id" in msg:
                            msg["role"] = "user"
                        if "role" not in msg:
                            msg["role"] = "user"  # Default to user role
                        if "content" not in msg and "message" in msg:
                            msg["content"] = msg["message"]
                        if "content" not in msg:
                            chat_history[i] = None  # Mark for removal
        
        # Remove any None values
        chat_history = [msg for msg in chat_history if msg is not None]
        
        # Make sure the current message is not already in the chat history
        # This prevents duplication when the LLM generates a response
        current_content = message.content.strip()
        chat_history = [msg for msg in chat_history if msg["content"].strip() != current_content]
        
        log_step("Chat", f"Using {len(chat_history)} messages from history and current message: '{current_content[:30]}...'")
        
        # Always enforce include_history=True to fix chat context issues
        if not message.include_history:
            logging.warning(f"Overriding include_history=False to ensure proper conversation context for session {session_id}")
            message.include_history = True
        
        # Check if streaming is requested and create queue if needed
        queue_id = None
        stream_processing = message.stream_processing
        
        if stream_processing:
            # Extract queue ID from metadata or headers
            if message.metadata and "queue_id" in message.metadata:
                queue_id = message.metadata["queue_id"]
            elif request.headers.get("X-Client-Queue-ID"):
                queue_id = request.headers.get("X-Client-Queue-ID")
                
            if queue_id:
                logging.info(f"Creating queue for message with queue_id: {queue_id}")
                if queue_id not in session_queues:
                    session_queues[queue_id] = queue.Queue()
                    logging.info(f"Created queue {queue_id} for message processing")
                
                # Send initial processing update
                session_queues[queue_id].put({
                    "type": "processing_update",
                    "stage": "analyzing_query",
                    "message": "Analyzing your query...",
                    "details": {},
                    "isCompleted": False,
                    "timestamp": time.time()
                })
                
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
        
        # Decide whether to use retrieval
        use_retrieval = message.use_retrieval if message.use_retrieval is not None else should_use_retrieval(message.content)
        
        log_step("Chat", f"Use retrieval: {use_retrieval}")
        
        # Send deciding_retrieval processing update
        if queue_id and queue_id in session_queues:
            session_queues[queue_id].put({
                "type": "processing_update",
                "stage": "deciding_retrieval",
                "message": f"Decided to {'use' if use_retrieval else 'skip'} retrieval",
                "details": {"use_retrieval": use_retrieval},
                "isCompleted": True,
                "timestamp": time.time()
            })
        
        # If using retrieval, get relevant chunks
        retrieved_chunks = []
        citations = []
        answer = ""
        
        if use_retrieval:
            log_step("Chat", "Retrieving relevant chunks...")
            
            # Send retrieving_documents processing update
            if queue_id and queue_id in session_queues:
                session_queues[queue_id].put({
                    "type": "processing_update",
                    "stage": "retrieving_documents",
                    "message": "Retrieving relevant documents...",
                    "details": {},
                    "isCompleted": False,
                    "timestamp": time.time()
                })
            
            # Get user_id from request state
            user_id = getattr(request.state, "user_id", None)
            
            # Split complex queries into simpler ones with chat history for context
            # Get chat history for context if include_history is true
            chat_context = chat_history if message.include_history else None
            log_step("Chat", f"Using chat history for query splitting: {bool(chat_context)}")
            
            # Pass chat history to query splitter for context awareness
            subqueries = split_query_into_subqueries(message.content, chat_history=chat_context)
            
            # If we managed to split the query, use the subqueries
            if len(subqueries) > 1:
                log_step("Chat", f"Split query into {len(subqueries)} subqueries with chat context")
                
                # Send splitting_query processing update
                if queue_id and queue_id in session_queues:
                    # Check if this is likely a follow-up query
                    is_likely_followup = len(message.content.split()) <= 5 and chat_context is not None
                    
                    # Add context information to the update
                    processing_details = {
                        "subQueries": subqueries,
                        "isFollowUp": is_likely_followup,
                        "contextUsed": chat_context is not None
                    }
                    
                    # Add the previous query for context if available
                    if is_likely_followup and chat_context and len(chat_context) > 0:
                        previous_user_query = next((msg["content"] for msg in reversed(chat_context) if msg["role"] == "user"), None)
                        if previous_user_query:
                            processing_details["previousQuery"] = previous_user_query
                    
                    # Send detailed update
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "splitting_query",
                        "message": f"Split query into {len(subqueries)} subqueries" + 
                                  (f" using context from previous messages" if chat_context else ""),
                        "details": processing_details,
                        "isCompleted": True,
                        "timestamp": time.time()
                    })
                
                # Process all subqueries in parallel
                retrieved_chunks = await retrieve_relevant_chunks_for_multiple_queries(
                    queries=subqueries,
                    filter_criteria=message.metadata.get("filter_criteria"),
                    top_k=message.metadata.get("n_results", 5),
                    user_id=user_id
                )
            else:
                # Just use the original query
                retrieved_chunks = await retrieve_relevant_chunks_async(
                    query=message.content,
                    filter_criteria=message.metadata.get("filter_criteria"),
                    top_k=message.metadata.get("n_results", 5),
                    user_id=user_id
                )
            
            # Send retrieving_documents completed update
            if queue_id and queue_id in session_queues:
                session_queues[queue_id].put({
                    "type": "processing_update",
                    "stage": "retrieving_documents",
                    "message": f"Retrieved {len(retrieved_chunks)} relevant chunks",
                    "details": {"chunk_count": len(retrieved_chunks)},
                    "isCompleted": True,
                    "timestamp": time.time()
                })
                
            # Generate answer using retrieved chunks
            if retrieved_chunks:
                # Send generating_answer processing update
                if queue_id and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "generating_answer",
                        "message": "Generating answer...",
                        "details": {},
                        "isCompleted": False,
                        "timestamp": time.time()
                    })
                
                # Format chat history for context
                formatted_history = chat_history if message.include_history else []
                
                # Generate answer
                result = await generate_answer_async(
                    query=message.content,
                    retrieved_chunks=retrieved_chunks,
                    chat_history=formatted_history,
                    user_id=user_id
                )
                
                answer = result["answer"]
                citations = result["citations"]
                log_step("Chat", f"Generated answer with {len(citations)} citations")
                
                # Send generating_answer completed update
                if queue_id and queue_id in session_queues:
                    session_queues[queue_id].put({
                        "type": "processing_update",
                        "stage": "generating_answer",
                        "message": "Answer generated successfully",
                        "details": {"citation_count": len(citations)},
                        "isCompleted": True,
                        "timestamp": time.time()
                    })
            else:
                answer = "I couldn't find any relevant information to answer your question."
        else:
            # No retrieval, generate answer directly
            log_step("Chat", "Generating answer without retrieval...")
            
            # Create a system prompt
            system_prompt = {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant providing concise and accurate information. "
                    "If you don't know the answer to something, simply state that you don't have that information."
                )
            }
            
            # Prepare messages for OpenAI
            messages = [system_prompt]
            
            # Add chat history if requested
            if message.include_history:
                for history_message in chat_history:
                    messages.append({
                        "role": history_message["role"],
                        "content": history_message["content"]
                    })
            
            # Add user message
            messages.append({
                "role": "user",
                "content": message.content
            })
            
            # Call OpenAI
            response = await asyncio.to_thread(
                azure_openai_client.chat.completions.create,
                model=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )
            
            answer = response.choices[0].message.content.strip()
        
        # Create AI message
        ai_message_id = str(uuid.uuid4())
        
        ai_message = {
            "message_id": ai_message_id,
            "session_id": session_id,
            "role": "assistant",
            "content": answer,
            "created_at": datetime.now().isoformat(),
            "citations": citations,
            "metadata": message.metadata or {}
        }
        
        # Add retrieved chunks to the message metadata for access in frontend
        if use_retrieval and retrieved_chunks:
            try:
                # Include the full context chunks that were retrieved and used in RAG
                ai_message["metadata"]["retrieved_chunks"] = [
                    {
                        "chunk_id": chunk.get("chunk_id", ""),
                        "document_id": chunk.get("metadata", {}).get("source_document_id", ""),
                        "document_name": chunk.get("metadata", {}).get("source_document_name", "Unknown"),
                        "text": chunk.get("text", ""),
                        "page_number": chunk.get("metadata", {}).get("page_number"),
                        "relevance_score": 1.0 - float(chunk.get("distance", 0.1)) if chunk.get("distance") is not None else 0.9,
                    }
                    for chunk in retrieved_chunks if chunk is not None
                ]
            except Exception as e:
                # Log error but continue without retrieved chunks
                log_step("Chat", f"Error adding retrieved chunks to metadata: {str(e)}", level="error")
        
        # Save AI message
        await save_message(ai_message)
        
        # Send completion update
        if queue_id and queue_id in session_queues:
            session_queues[queue_id].put({
                "type": "processing_update",
                "stage": "complete",
                "message": "Response is ready",
                "details": {"complete": True},
                "isCompleted": True,
                "timestamp": time.time()
            })
        
        # Return the AI message
        return MessageResponse(**ai_message)
        
    except Exception as e:
        log_step("Chat", f"Error processing message: {str(e)}", level="error")
        logging.error(f"Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@router.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    request: Request,
    message_id: str = Path(..., description="Message ID")
):
    """
    Get a specific message by ID.
    
    Args:
        request: Request object with user ID in state
        message_id: Message ID
    
    Returns:
        Message details if the message belongs to a session owned by the current user
    """
    with Timer("Get Message"):
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        
        if message_id not in chat_messages:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message = chat_messages[message_id]
        
        # Check if the message's session belongs to the current user
        if user_id and message.session_id in chat_sessions:
            session = chat_sessions[message.session_id]
            if session.user_id != user_id:
                logging.warning(f"User {user_id} attempted to access message {message_id} in session {message.session_id} owned by {session.user_id}")
                raise HTTPException(status_code=403, detail="You don't have permission to access this message")
        
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
async def get_message_citations(
    request: Request,
    message_id: str = Path(..., description="Message ID")
):
    """
    Get citations for a specific message.
    
    Args:
        request: Request object with user ID in state
        message_id: Message ID
    
    Returns:
        List of citations if the message belongs to a session owned by the current user
    """
    with Timer("Get Message Citations"):
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        
        if message_id not in chat_messages:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message = chat_messages[message_id]
        
        # Check if the message's session belongs to the current user
        if user_id and message.session_id in chat_sessions:
            session = chat_sessions[message.session_id]
            if session.user_id != user_id:
                logging.warning(f"User {user_id} attempted to access citations for message {message_id} in session {message.session_id} owned by {session.user_id}")
                raise HTTPException(status_code=403, detail="You don't have permission to access these citations")
        
        return {"citations": message.citations}

@router.get("/messages/{message_id}/retrieved_chunks")
async def get_message_retrieved_chunks(
    request: Request,
    message_id: str = Path(..., description="Message ID")
):
    """
    Get all retrieved chunks used to generate a specific message.
    
    Args:
        request: Request object with user ID in state
        message_id: Message ID
    
    Returns:
        List of retrieved chunks if the message belongs to a session owned by the current user
    """
    with Timer("Get Message Retrieved Chunks"):
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        
        if message_id not in chat_messages:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message = chat_messages[message_id]
        
        # Check if the message's session belongs to the current user
        if user_id and message.session_id in chat_sessions:
            session = chat_sessions[message.session_id]
            if session.user_id != user_id:
                logging.warning(f"User {user_id} attempted to access retrieved chunks for message {message_id} in session {message.session_id} owned by {session.user_id}")
                raise HTTPException(status_code=403, detail="You don't have permission to access these chunks")
        
        # Return the retrieved chunks if available in metadata
        retrieved_chunks = message.metadata.get("retrieved_chunks", [])
        return {"retrieved_chunks": retrieved_chunks}

@router.get("/citations/{document_id}/{chunk_id}")
async def get_citation_source(
    request: Request,
    document_id: str = Path(..., description="Document ID"),
    chunk_id: str = Path(..., description="Chunk ID")
):
    """
    Get the source information for a citation.
    
    Args:
        request: Request object
        document_id: Document ID
        chunk_id: Chunk ID
    
    Returns:
        Source information with context
    """
    with Timer("Get Citation Source"):
        # Get document details
        document = get_user_storage(request).get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get chunk details
        chunks = get_user_storage(request).get_document_chunks(document_id)
        
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
    request: Request,
    session_id: str = Path(..., description="Chat session ID"),
    include_citations: bool = Query(True, description="Include detailed citation information")
):
    """
    Export a chat session with all messages and citations.
    
    Args:
        request: Request object with user ID in state
        session_id: Chat session ID
        include_citations: Whether to include detailed citation information
    
    Returns:
        Complete chat export if the session is owned by the current user
    """
    with Timer("Export Chat Session"):
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        # Verify that the session belongs to the current user
        if user_id and session.user_id != user_id:
            logging.warning(f"User {user_id} attempted to export session {session_id} owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to export this chat session")
        
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

@router.post("/batch/messages", response_model=List[MessageResponse])
async def batch_process_messages(
    request: Request,
    messages: List[SendMessageRequest],
    session_id: str = Query(..., description="Chat session ID")
):
    """
    Process multiple messages in parallel for a chat session.
    
    Args:
        request: Request object with user ID in state
        messages: List of messages to process
        session_id: Chat session ID
    
    Returns:
        List of AI response messages if the session is owned by the current user
    """
    try:
        # Get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        logging.info(f"Batch processing messages for user: {user_id}")
        
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Verify that the session belongs to the current user
        session = chat_sessions[session_id]
        if user_id and session.user_id != user_id:
            logging.warning(f"User {user_id} attempted to batch process messages for session {session_id} owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to send messages to this chat session")
        
        # Create a queue for this batch request if needed
        batch_queue_id = f"batch_{session_id}_{str(uuid.uuid4())}"
        
        # Create a timer callback using the same pattern as single messages
        def create_batch_timer_callback(current_queue_id):
            def callback(stage: str, details: Dict[str, Any]):
                # Only use if queue exists
                if current_queue_id in session_queues:
                    session_queues[current_queue_id].put({
                        "type": "batch_processing_update",
                        "stage": stage,
                        "message": f"{details.get('operation', 'Operation')} {details.get('status', '')}",
                        "details": details
                    })
            return callback
            
        # Create the timer callback for this batch request
        batch_timer = create_batch_timer_callback(batch_queue_id)
        
        with Timer(f"Batch Process {len(messages)} Messages", batch_timer):
            if session_id not in chat_sessions:
                raise HTTPException(status_code=404, detail="Chat session not found")
            
            # Update session
            session = chat_sessions[session_id]
            session.updated_at = datetime.now()
            
            # Get chat history for context with user verification
            chat_history = await get_chat_history_for_context(session_id, user_id)
            
            # Process all messages in parallel
            user_message_ids = []
            user_messages = []
            
            # Get user_id from request state
            user_id = getattr(request.state, "user_id", None)
            logging.info(f"Batch processing messages for user: {user_id}")
            
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
            
            # Retrieve chunks for all queries in parallel
            with Timer("Retrieve Chunks", batch_timer):
                retrieval_tasks = [
                    retrieve_relevant_chunks_async(
                        query=query,
                        filter_criteria=None,
                        top_k=5,
                        user_id=user_id
                    )
                    for query in queries
                ]
                
                all_retrieved_chunks = await asyncio.gather(*retrieval_tasks)
            
            # Generate answers for all queries in parallel
            with Timer("Generate Answers", batch_timer):
                results = await batch_generate_answers(
                    queries=queries,
                    retrieved_chunks_list=all_retrieved_chunks,
                    chat_histories=[chat_history] * len(queries),
                    user_id=user_id
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

    except Exception as e:
        log_step("Chat", f"Error processing batch messages: {str(e)}", level="error")
        
        # Send error update
        if batch_queue_id in locals() and batch_queue_id in session_queues:
            session_queues[batch_queue_id].put({
                "type": "batch_processing_update",
                "stage": "complete",
                "message": f"Error: {str(e)}",
                "details": {"error": True}
            })
            
        raise HTTPException(status_code=500, detail=f"Error processing batch messages: {str(e)}")

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
    logging.info(f"Received regular stream request for queue_id: {queue_id}")
    logging.info(f"Active queues: {list(session_queues.keys())}")
    
    # Get user ID from request state
    user_id = getattr(request.state, "user_id", None)
    logging.info(f"Streaming updates for user: {user_id}")
    
    # Initialize queue if it doesn't exist
    if queue_id not in session_queues:
        logging.info(f"Creating queue for queue_id: {queue_id}")
        session_queues[queue_id] = queue.Queue()
        # Send an initial message to the queue
        session_queues[queue_id].put({
            "type": "connection_established",
            "message": "Server connection established",
            "timestamp": time.time()
        })
    
    # Set proper headers for SSE
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Transfer-Encoding": "chunked",
        # CORS headers for browser support
        "Access-Control-Allow-Headers": "Content-Type",
    }
    
    # Check the request origin to set correct CORS headers
    origin = request.headers.get("origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    else:
        headers["Access-Control-Allow-Origin"] = "*"
        
    logging.info(f"Setting SSE response headers: {headers}")
    
    return StreamingResponse(
        stream_events(queue_id, user_id),
        media_type="text/event-stream",
        headers=headers
    )

@router.get("/sessions/{session_id}/realtime-stream/{queue_id}")
async def realtime_stream_updates(
    request: Request,
    session_id: str,
    queue_id: str
):
    """
    Stream processing updates in real-time using Server-Sent Events (SSE).
    This endpoint guarantees immediate delivery of events without batching.
    
    Args:
        request: FastAPI request
        session_id: Chat session ID
        queue_id: Queue ID for this specific request
        
    Returns:
        SSE streaming response with no buffering
    """
    logging.info(f"Received streaming request for queue_id: {queue_id}")
    logging.info(f"Active queues: {list(session_queues.keys())}")
    
    # Get user ID from request state
    user_id = getattr(request.state, "user_id", None)
    logging.info(f"Streaming realtime updates for user: {user_id}")
    
    # Initialize queue if it doesn't exist
    if queue_id not in session_queues:
        logging.info(f"Creating queue for queue_id: {queue_id}")
        session_queues[queue_id] = queue.Queue()
        # Send an initial message to the queue
        session_queues[queue_id].put({
            "type": "connection_established",
            "message": "Server connection established",
            "timestamp": time.time()
        })
    
    # Set proper headers for SSE with no buffering
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
        "Transfer-Encoding": "chunked",
        # Add CORS headers for browser support
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    
    # Check the request origin to set correct CORS headers
    origin = request.headers.get("origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        
    logging.info(f"Setting SSE response headers: {headers}")
    
    return StreamingResponse(
        realtime_stream_events(queue_id, user_id),
        media_type="text/event-stream",
        headers=headers
    )

async def stream_events(queue_id: str, user_id: Optional[str] = None):
    """
    Async generator function for SSE streaming.
    
    Args:
        queue_id: Queue ID for this specific request
        user_id: Optional user ID for user-specific processing
        
    Yields:
        SSE formatted events
    """
    # Ensure queue exists
    if queue_id not in session_queues:
        logging.error(f"Queue ID {queue_id} not found in session_queues when starting stream_events")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Stream not found', 'code': 404, 'error': True})}\n\n"
        return
    
    q = session_queues[queue_id]
    
    try:
        # Send initial connection established event
        yield f"data: {json.dumps({'type': 'connection_established'})}\n\n"
        # Force flush
        yield f": flush-{time.time()}\n\n"
        
        # Create asyncio queue for async handling
        asyncio_queue = asyncio.Queue()
        
        # Create task to move items from queue to asyncio queue
        async def queue_consumer():
            try:
                # Transfer any existing items
                while not q.empty():
                    try:
                        data = q.get_nowait()
                        await asyncio_queue.put(data)
                    except queue.Empty:
                        break
                
                # Poll for new items
                while queue_id in session_queues:
                    try:
                        try:
                            data = q.get_nowait()
                            await asyncio_queue.put(data)
                        except queue.Empty:
                            # No new items, send heartbeat occasionally
                            if int(time.time()) % 10 == 0:  # Every 10 seconds
                                await asyncio_queue.put({"type": "heartbeat", "timestamp": time.time()})
                            
                            # Sleep to avoid tight polling
                            await asyncio.sleep(0.1)
                    except Exception as e:
                        logging.error(f"Error in queue consumer: {str(e)}")
                        await asyncio.sleep(0.1)
            except Exception as e:
                logging.error(f"Fatal error in queue consumer: {str(e)}")
                try:
                    await asyncio_queue.put({
                        "type": "error",
                        "message": f"Server error: {str(e)}",
                        "timestamp": time.time()
                    })
                except:
                    pass
        
        # Start the consumer task
        consumer_task = asyncio.create_task(queue_consumer())
        
        # Immediately send ready event without delay
        yield f"data: {json.dumps({'type': 'stream_ready'})}\n\n"
        yield f": flush-{time.time()}\n\n"
        
        try:
            while True:
                try:
                    # Get next item with timeout
                    data = await asyncio.wait_for(asyncio_queue.get(), timeout=1.0)
                    
                    # Log the event being sent
                    logging.info(f"Streaming event: {json.dumps(data)}")
                    
                    # Send the data as an SSE event with timestamp
                    event_with_ts = data.copy() if isinstance(data, dict) else {"data": data}
                    if isinstance(event_with_ts, dict):
                        event_with_ts["timestamp"] = time.time()
                    
                    # Send the data immediately
                    yield f"data: {json.dumps(event_with_ts)}\n\n"
                    
                    # Force flush immediately
                    yield f": flush-{time.time()}\n\n"
                    
                    # Small sleep to ensure client processing
                    await asyncio.sleep(0.01)
                    
                    # Check for complete event
                    if isinstance(data, dict) and data.get("type") == "processing_update" and data.get("stage") == "complete":
                        logging.info(f"Complete event detected, preparing to close stream for {queue_id}")
                        yield f"data: {json.dumps({'type': 'closing', 'message': 'Stream will close shortly', 'timestamp': time.time()})}\n\n"
                        yield f": flush-{time.time()}\n\n"
                        break
                    
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': time.time()})}\n\n"
                    yield f": flush-{time.time()}\n\n"
                    
                    # Check if we should exit
                    if queue_id not in session_queues:
                        break
        finally:
            # Clean up the consumer task
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
    except GeneratorExit:
        # Clean up when client disconnects
        if queue_id in session_queues:
            del session_queues[queue_id]
            logging.info(f"Cleaned up stream resources for {queue_id}")

async def realtime_stream_events(queue_id: str, user_id: Optional[str] = None):
    """
    Asynchronous generator function for real-time SSE streaming.
    This implementation ensures events are delivered immediately.
    
    Args:
        queue_id: Queue ID for this specific request
        user_id: Optional user ID for user-specific processing
        
    Yields:
        SSE formatted events with immediate flush commands
    """
    # Ensure queue exists
    if queue_id not in session_queues:
        logging.error(f"Queue ID {queue_id} not found in session_queues when starting realtime_stream_events")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Stream not found', 'code': 404, 'error': True})}\n\n"
        return
    
    q = session_queues[queue_id]
    
    try:
        # Log connection start
        logging.info(f"Starting realtime stream for queue_id: {queue_id}")
        
        # Send initial connection established event
        yield f"data: {json.dumps({'type': 'connection_established'})}\n\n"
        # Send empty comment to force flush
        yield f": flush-{time.time()}\n\n"
        
        # Use asyncio queue for async handling of events
        asyncio_queue = asyncio.Queue()
        
        # Create a background task to move items from the queue to the asyncio queue
        async def queue_consumer():
            try:
                # Transfer all existing items in the queue first
                while not q.empty():
                    try:
                        data = q.get_nowait()
                        await asyncio_queue.put(data)
                        logging.info(f"Transferred existing event to async queue: {data.get('type', 'unknown') if isinstance(data, dict) else 'unknown'}")
                    except queue.Empty:
                        break
                
                # Poll the queue regularly
                while queue_id in session_queues:
                    try:
                        # Check for new items without blocking
                        try:
                            data = q.get_nowait()
                            await asyncio_queue.put(data)
                            if isinstance(data, dict) and data.get('type') != 'heartbeat':
                                logging.info(f"Transferred event to async queue: {data.get('type', 'unknown')}")
                        except queue.Empty:
                            # No items, send heartbeat occasionally and sleep
                            if int(time.time()) % 5 == 0:  # Heartbeat every 5 seconds
                                await asyncio_queue.put({"type": "heartbeat", "timestamp": time.time()})
                            
                            # Short sleep to avoid tight polling
                            await asyncio.sleep(0.05)
                    except Exception as e:
                        logging.error(f"Error in queue consumer: {str(e)}")
                        await asyncio.sleep(0.1)
            except Exception as e:
                logging.error(f"Fatal error in queue consumer: {str(e)}")
                await asyncio_queue.put({
                    "type": "error",
                    "message": f"Server error: {str(e)}",
                    "timestamp": time.time()
                })
        
        # Start the consumer task
        consumer_task = asyncio.create_task(queue_consumer())
        
        # Send a test event to verify the stream is working
        yield f"data: {json.dumps({'type': 'test', 'message': 'Stream connection test', 'timestamp': time.time()})}\n\n"
        yield f": flush-{time.time()}\n\n"
        
        # Process items from the asyncio queue
        heartbeat_counter = 0
        
        try:
            while True:
                # Use a timeout to allow for heartbeats and checking if the connection should be closed
                try:
                    # Get next item with a short timeout
                    data = await asyncio.wait_for(asyncio_queue.get(), timeout=0.5)
                    
                    # Skip logging for heartbeats to reduce noise
                    if data.get("type") == "heartbeat":
                        heartbeat_counter += 1
                        if heartbeat_counter % 10 == 0:  # Log every 10th heartbeat
                            logging.info(f"Sent {heartbeat_counter} heartbeats")
                    else:
                        # Log the event being sent
                        logging.info(f"Streaming event: {json.dumps(data)}")
                    
                    # Add timestamp to prevent browser buffering
                    if isinstance(data, dict):
                        data["timestamp"] = time.time()
                    
                    # Send each event immediately with a yield
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    # Add flush directive to force immediate delivery
                    yield f": flush-{time.time()}\n\n"
                    
                    # Use a small sleep to ensure the event is processed by the client
                    await asyncio.sleep(0.01)
                    
                    # If we're seeing a complete event, prepare to close the connection
                    if isinstance(data, dict) and data.get("type") == "processing_update" and data.get("stage") == "complete":
                        logging.info(f"Complete event detected, preparing to close stream for {queue_id}")
                        yield f"data: {json.dumps({'type': 'closing', 'message': 'Stream will close shortly', 'timestamp': time.time()})}\n\n"
                        yield f": flush-{time.time()}\n\n"
                        
                        # Give a moment for any final events to be processed
                        await asyncio.sleep(0.1)
                        break
                    
                except asyncio.TimeoutError:
                    # Send heartbeat after timeout
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                    yield f": flush-{time.time()}\n\n"
                    
                    # Check if we should exit (e.g., client disconnected)
                    if queue_id not in session_queues:
                        logging.info(f"Queue {queue_id} no longer exists, closing stream")
                        break
        finally:
            # Clean up the consumer task
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
                
    except GeneratorExit:
        # Clean up when client disconnects
        logging.info(f"Client disconnected from realtime stream {queue_id}")
    except Exception as e:
        # Send error to client before exiting
        error_msg = str(e)
        logging.error(f"Error in realtime stream: {error_msg}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Server error: {error_msg}', 'timestamp': time.time()})}\n\n"
        yield f": flush-{time.time()}\n\n"
    finally:
        # Clean up resources
        if queue_id in session_queues:
            del session_queues[queue_id]
        
        # Log cleanup
        logging.info(f"Cleaned up stream resources for {queue_id}")