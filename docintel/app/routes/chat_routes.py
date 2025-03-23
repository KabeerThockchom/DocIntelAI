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
        session_id: Chat session ID
        message: Message content and metadata
        parallel_processing: Whether to use parallel processing for RAG
        response: FastAPI response object for setting headers
        
    Returns:
        Message response with AI-generated content
    """
    try:
        # Ensure we have a response object to set headers
        if response is None:
            response = Response()
            logging.warning("Response object was None in send_message, created new Response")
        
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
        
        # Check for client-provided queue ID first (check in both headers and message metadata)
        client_queue_id = request.headers.get('X-Client-Queue-ID', None)
        if not client_queue_id and message.metadata and 'queue_id' in message.metadata:
            client_queue_id = message.metadata.get('queue_id')
            
        # Create a queue for this request if streaming is enabled
        queue_id = client_queue_id if client_queue_id else f"{session_id}_{str(uuid.uuid4())}"
        logging.info(f"Using queue_id: {queue_id} {'(client-provided)' if client_queue_id else '(server-generated)'}")
        
        if message.stream_processing:
            # Create persistent queue for this request
            session_queues[queue_id] = queue.Queue()
            logging.info(f"Created queue for {queue_id}. Currently {len(session_queues)} active queues")
            
            # Send initial processing update using the realtime update function
            send_realtime_update(
                session_queues.get(queue_id),
                "analyzing_query",
                "Analyzing your question...",
                {"queue_id": queue_id, "realtime": True},
                False
            )
            
            # Set the queue_id in the response headers (always use response here)
            logging.info(f"Setting X-Queue-ID header to {queue_id}")
            response.headers["X-Queue-ID"] = queue_id
            # Add a header to indicate the realtime endpoint should be used
            response.headers["X-Realtime-Stream"] = "true"
            
            # For debugging, add additional headers that might help identify issues
            response.headers["Access-Control-Expose-Headers"] = "X-Queue-ID, X-Realtime-Stream"
            
            # Log all response headers for debugging
            logging.info(f"Response headers: {dict(response.headers.items())}")
        else:
            logging.info("Stream processing is disabled, not setting queue_id in headers")
        
        # Create a timer callback function to send real-time updates
        # Use a closure to capture the queue_id
        def create_timer_callback(current_queue_id):
            def callback(stage: str, details: Dict[str, Any]):
                # Skip if queue is gone or streaming is disabled
                if not message.stream_processing or current_queue_id not in session_queues:
                    return
                
                update_stage = "analyzing_query"  # Default
                
                # Map operation stages to processing stages
                if "retrieval_decision" in stage:
                    update_stage = "deciding_retrieval"
                elif "query_splitting" in stage:
                    update_stage = "splitting_query"
                elif "retrieve_chunks" in stage or "chroma_query" in stage:
                    update_stage = "retrieving_documents"
                elif "generate_answer" in stage:
                    update_stage = "generating_answer"
                
                # Check if operation is completed based on stage name
                is_completed = "_completed" in stage
                
                # Create update message
                update_message = f"{details.get('operation', 'Operation')} {details.get('status', '')}"
                if details.get('progress') is not None:
                    update_message += f" ({int(details['progress'] * 100)}%)"
                
                # Use helper function to send updates
                if is_completed:
                    complete_message = f"{details.get('operation', 'Operation')} completed"
                    if details.get('duration') is not None:
                        complete_message += f" in {details['duration']:.2f}s"
                    
                    # Mark step as completed
                    send_realtime_update(
                        session_queues.get(current_queue_id),
                        update_stage,
                        complete_message,
                        details,
                        True  # This step is completed
                    )
                    
                    # When a step completes, immediately send an update to start the next step
                    stages = ["analyzing_query", "deciding_retrieval", "splitting_query", 
                            "retrieving_documents", "generating_answer"]
                    current_index = stages.index(update_stage)
                    
                    if current_index < len(stages) - 1:
                        next_stage = stages[current_index + 1]
                        # Immediately start the next step without delay for better real-time experience
                        send_realtime_update(
                            session_queues.get(current_queue_id),
                            next_stage,
                            f"Starting {next_stage.replace('_', ' ')}...",
                            {},
                            False  # Next step is starting
                        )
                else:
                    # Regular progress update (not completed)
                    send_realtime_update(
                        session_queues.get(current_queue_id),
                        update_stage,
                        update_message,
                        details,
                        False  # In progress
                    )
            return callback
        
        # Create a timer callback specifically for this request
        timer_callback = create_timer_callback(queue_id)
        
        # If use_retrieval is not explicitly set to False, let the LLM decide
        if use_retrieval is not False:
            # Notify we're starting the retrieval decision
            if message.stream_processing and queue_id in session_queues:
                send_realtime_update(
                    session_queues.get(queue_id),
                    "deciding_retrieval",
                    "Determining if document retrieval is needed...",
                    {"queue_id": queue_id},
                    False
                )
                
            # Pass chat history to the retrieval decision function if include_history is True
            history_for_decision = chat_history if message.include_history else []
            
            # Use the timer with callback for retrieval decision
            with Timer("Retrieval Decision", timer_callback):
                retrieval_decision = should_use_retrieval(message.content, history_for_decision)
            
            # Check the format of the retrieval_decision and handle accordingly
            if isinstance(retrieval_decision, dict) and "should_retrieve" in retrieval_decision:
                use_retrieval = retrieval_decision["should_retrieve"]
                retrieval_confidence = retrieval_decision.get("confidence", 0.0)
                retrieval_reasoning = retrieval_decision.get("reasoning", "")
            else:
                # Fallback to the old format or default value
                use_retrieval = retrieval_decision.get("retrieval_needed", True)
                retrieval_confidence = 0.0
                retrieval_reasoning = retrieval_decision.get("reasoning", "")
            
            # Send retrieval decision update if streaming is enabled
            if message.stream_processing and queue_id in session_queues:
                send_realtime_update(
                    session_queues.get(queue_id),
                    "deciding_retrieval",
                    f"{'Using' if use_retrieval else 'Not using'} document retrieval (confidence: {retrieval_confidence:.2f})",
                    {
                        "should_retrieve": use_retrieval,
                        "confidence": retrieval_confidence,
                        "reasoning": retrieval_reasoning,
                        "queue_id": queue_id
                    },
                    True  # Mark deciding_retrieval as completed
                )
        else:
            retrieval_reasoning = "User explicitly disabled retrieval"
            
            # Send retrieval decision update
            if message.stream_processing and queue_id in session_queues:
                send_realtime_update(
                    session_queues.get(queue_id),
                    "deciding_retrieval",
                    "Retrieval disabled by user",
                    {"retrievalNeeded": False},
                    True  # Mark deciding_retrieval as completed
                )
        
        # Start with empty citations list for AI message
        citations = []
        
        # Use RAG pipeline if retrieval is enabled
        if use_retrieval:
            # Notify we're starting to split the query
            if message.stream_processing and queue_id in session_queues:
                send_realtime_update(
                    session_queues.get(queue_id),
                    "splitting_query",
                    "Breaking down your question into searchable components...",
                    {"queue_id": queue_id},
                    False
                )
                
            # Split the query into sub-queries for better retrieval
            log_step("RAG", f"Splitting query into sub-queries: {message.content}...")
            
            # Use the timer with callback for query splitting
            with Timer("Query Splitting", timer_callback):
                sub_queries = split_query_into_subqueries(message.content, chat_history if message.include_history else None)
            
            # Always ensure sub_queries is a list, even if the query wasn't split
            if not sub_queries or len(sub_queries) == 0:
                sub_queries = [message.content]
                log_step("RAG", f"Using original query as the only sub-query: {message.content}")
            
            # Send sub-queries in streaming update immediately when available
            if message.stream_processing and queue_id in session_queues:
                # Create a detailed message about the query splitting
                split_message = f"Split query into {len(sub_queries)} sub-queries"
                if len(sub_queries) == 1:
                    split_message = "Using your question directly for search"
                
                # Send detailed update with sub-queries for visualization
                query_update = {
                    "type": "processing_update",
                    "stage": "splitting_query",
                    "message": split_message,
                    "queue_id": queue_id,
                    "details": {
                        "original_query": message.content,
                        "sub_queries": sub_queries,
                        "subQueries": sub_queries  # Add both formats for backward compatibility
                    },
                    "subQueries": sub_queries,  # Add directly to the top level for easier frontend access
                    "isCompleted": True,
                    "progressPercentage": 40  # 40% progress at this stage
                }
                
                # Ensure this event is sent and processed before moving on
                session_queues[queue_id].put(query_update)
            
            # Notify we're starting to retrieve documents
            if message.stream_processing and queue_id in session_queues:
                retrieval_steps = [
                    "Preparing search query",
                    "Searching document database",
                    "Ranking relevant documents",
                    "Extracting context from documents"
                ]
                send_realtime_update(
                    session_queues.get(queue_id),
                    "retrieving_documents",
                    "Searching through your documents...",
                    {
                        "queue_id": queue_id,
                        "steps": retrieval_steps,
                        "current_step": retrieval_steps[0],
                        "completed_steps": []
                    },
                    False
                )
                
            # Retrieve chunks for all sub-queries asynchronously with progress updates
            completed_retrieval_steps = []
            
            # Custom progress tracking for retrieval
            async def retrieval_progress_tracker(step_index, status="in_progress"):
                if not message.stream_processing or queue_id not in session_queues:
                    return
                
                retrieval_steps = [
                    "Preparing search query",
                    "Searching document database",
                    "Ranking relevant documents",
                    "Extracting context from documents"
                ]
                
                if status == "completed" and step_index < len(retrieval_steps):
                    completed_retrieval_steps.append(retrieval_steps[step_index])
                    next_step_idx = step_index + 1
                    current_step = retrieval_steps[next_step_idx] if next_step_idx < len(retrieval_steps) else None
                else:
                    current_step = retrieval_steps[step_index] if step_index < len(retrieval_steps) else None
                
                step_message = f"Step {step_index+1}/{len(retrieval_steps)}: {current_step}" if current_step else "Finalizing retrieval"
                
                send_realtime_update(
                    session_queues.get(queue_id),
                    "retrieving_documents",
                    step_message,
                    {
                        "queue_id": queue_id,
                        "steps": retrieval_steps,
                        "current_step": current_step,
                        "completed_steps": completed_retrieval_steps.copy()
                    },
                    False
                )
            
            # Update progress for first step
            await retrieval_progress_tracker(0)
            
            # Original timer callback for compatibility
            with Timer("Retrieve Chunks", timer_callback):
                # Step 1: Prepare query
                await retrieval_progress_tracker(0, "completed")
                
                # Step 2: Search database
                await retrieval_progress_tracker(1)
                
                # Actual retrieval
                retrieved_chunks = await retrieve_relevant_chunks_for_multiple_queries(
                    queries=sub_queries,
                    top_k=10
                )
                
                # Step 2 completed
                await retrieval_progress_tracker(1, "completed")
                
                # Step 3: Ranking documents
                await retrieval_progress_tracker(2)
                await retrieval_progress_tracker(2, "completed")
                
                # Step 4: Extract context
                await retrieval_progress_tracker(3)
                await retrieval_progress_tracker(3, "completed")
            
            # Send retrieval update as soon as we have the chunks
            if message.stream_processing and queue_id in session_queues:
                retrieval_steps = [
                    "Preparing search query",
                    "Searching document database",
                    "Ranking relevant documents",
                    "Extracting context from documents"
                ]
                send_realtime_update(
                    session_queues.get(queue_id),
                    "retrieving_documents",
                    f"Found {len(retrieved_chunks)} relevant chunks from your documents",
                    {
                        "chunkCount": len(retrieved_chunks),
                        "steps": retrieval_steps,
                        "completed_steps": retrieval_steps  # All steps are completed
                    },
                    True  # Mark retrieving_documents as completed
                )
            
            # Notify we're starting to generate the answer
            if message.stream_processing and queue_id in session_queues:
                generation_steps = [
                    "Analyzing retrieved documents",
                    "Synthesizing information",
                    "Drafting response",
                    "Formatting citations"
                ]
                send_realtime_update(
                    session_queues.get(queue_id),
                    "generating_answer",
                    "Generating a comprehensive answer...",
                    {
                        "steps": generation_steps,
                        "current_step": generation_steps[0],
                        "completed_steps": []
                    },
                    False
                )
            
            # Format chat history if include_history is True
            context_history = chat_history if message.include_history else None
            
            # Completed generation steps tracking
            completed_generation_steps = []
            
            # Function to track generation progress
            async def generation_progress_tracker(step_index, status="in_progress"):
                if not message.stream_processing or queue_id not in session_queues:
                    return
                
                generation_steps = [
                    "Analyzing retrieved documents",
                    "Synthesizing information",
                    "Drafting response",
                    "Formatting citations"
                ]
                
                if status == "completed" and step_index < len(generation_steps):
                    completed_generation_steps.append(generation_steps[step_index])
                    next_step_idx = step_index + 1
                    current_step = generation_steps[next_step_idx] if next_step_idx < len(generation_steps) else None
                else:
                    current_step = generation_steps[step_index] if step_index < len(generation_steps) else None
                
                step_message = f"Step {step_index+1}/{len(generation_steps)}: {current_step}" if current_step else "Finalizing answer"
                
                send_realtime_update(
                    session_queues.get(queue_id),
                    "generating_answer",
                    step_message,
                    {
                        "steps": generation_steps,
                        "current_step": current_step,
                        "completed_steps": completed_generation_steps.copy()
                    },
                    False
                )
            
            # Start tracking first generation step
            await generation_progress_tracker(0)
            
            # Use the timer with callback for answer generation
            with Timer("Generate Answer", timer_callback):
                # Step 1: Analyze documents
                await generation_progress_tracker(0, "completed")
                
                # Step 2: Synthesize information
                await generation_progress_tracker(1)
                
                # Start the actual generation process
                partial_result = None
                async def generation_background_updates():
                    # Send periodic updates for Step 2 & 3 to show ongoing progress
                    for i in range(5):  # Send a few periodic updates
                        if queue_id not in session_queues:
                            break
                        if partial_result is not None:
                            break
                            
                        # Add actual progress updates without sleeps
                        step_message = f"Working on your answer... ({i+1}/5)"
                        send_realtime_update(
                            session_queues.get(queue_id),
                            "generating_answer",
                            step_message,
                            {
                                "steps": generation_steps,
                                "current_step": "Drafting response",
                                "completed_steps": completed_generation_steps.copy(),
                                "progress_indicator": i+1
                            },
                            False
                        )
                
                # Start background updates
                background_task = asyncio.create_task(generation_background_updates())
                
                # Complete step 2
                await generation_progress_tracker(1, "completed")
                
                # Step 3: Drafting response
                await generation_progress_tracker(2)
                
                # Actual generation
                result = await generate_answer_async(
                    query=message.content,
                    retrieved_chunks=retrieved_chunks,
                    chat_history=context_history
                )
                
                # Mark result as ready
                partial_result = result
                
                # Wait for background task to finish
                await background_task
                
                # Complete step 3
                await generation_progress_tracker(2, "completed")
                
                # Step 4: Format citations
                await generation_progress_tracker(3)
                await generation_progress_tracker(3, "completed")
            
            # Final update - all steps completed
            if message.stream_processing and queue_id in session_queues:
                generation_steps = [
                    "Analyzing retrieved documents",
                    "Synthesizing information",
                    "Drafting response",
                    "Formatting citations"
                ]
                send_realtime_update(
                    session_queues.get(queue_id),
                    "generating_answer",
                    "Answer generation complete!",
                    {
                        "steps": generation_steps,
                        "completed_steps": generation_steps  # All steps completed
                    },
                    True  # Mark generating_answer as completed
                )
            
            # Get the answer and citations
            answer = result["answer"]
            citations = result["citations"]
            
            log_step("RAG", f"Generated answer with {len(citations)} citations")
            
        else:
            # No retrieval needed, generate answer without context
            # Notify we're starting to generate the answer
            if message.stream_processing and queue_id in session_queues:
                send_realtime_update(
                    session_queues.get(queue_id),
                    "generating_answer",
                    "Generating a direct answer...",
                    {},
                    False
                )
            
            # Use the timer with callback for answer generation even without retrieval
            with Timer("Generate Answer", timer_callback):
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
                
                # Generate answer using Azure OpenAI
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
        if use_retrieval and 'retrieved_chunks' in locals():
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
        if message.stream_processing and queue_id in session_queues:
            send_realtime_update(
                session_queues.get(queue_id),
                "complete",
                "Response generated successfully",
                {},
                True  # Mark as completed
            )
        
        # Return the AI message
        return MessageResponse(**ai_message)
        
    except Exception as e:
        log_step("Chat", f"Error processing message: {str(e)}", level="error")
        
        # Send error update
        if message.stream_processing and 'queue_id' in locals() and queue_id in session_queues:
            send_realtime_update(
                session_queues.get(queue_id),
                "complete",
                f"Error: {str(e)}",
                {"error": True},
                True  # Mark as completed
            )
            
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

@router.get("/messages/{message_id}/retrieved_chunks")
async def get_message_retrieved_chunks(message_id: str = Path(..., description="Message ID")):
    """
    Get all retrieved chunks used to generate a specific message.
    
    Args:
        message_id: Message ID
    
    Returns:
        List of retrieved chunks with document information
    """
    with Timer("Get Message Retrieved Chunks"):
        if message_id not in chat_messages:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message = chat_messages[message_id]
        
        # Return the retrieved chunks if available in metadata
        retrieved_chunks = message.metadata.get("retrieved_chunks", [])
        return {"retrieved_chunks": retrieved_chunks}

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
    try:
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
            
            # Retrieve chunks for all queries in parallel
            retrieval_tasks = [
                retrieve_relevant_chunks_async(query)
                for query in queries
            ]
            
            with Timer("Retrieve Chunks", batch_timer):
                all_retrieved_chunks = await asyncio.gather(*retrieval_tasks)
            
            # Generate answers for all queries in parallel
            with Timer("Generate Answers", batch_timer):
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
    
    # Check if queue exists
    if queue_id not in session_queues:
        logging.error(f"Queue ID {queue_id} not found in session_queues")
        # Return an error response but with correct content type for SSE
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        }
        
        # Create a simple generator to return error and close
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream not found', 'code': 404, 'error': True})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers=headers
        )
    
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
        stream_events(queue_id),
        media_type="text/event-stream",
        headers=headers
    )

async def stream_events(queue_id: str):
    """
    Async generator function for SSE streaming.
    
    Args:
        queue_id: Queue ID for this specific request
        
    Yields:
        SSE formatted events
    """
    if queue_id not in session_queues:
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
    
    # Check if queue exists
    if queue_id not in session_queues:
        logging.error(f"Queue ID {queue_id} not found in session_queues")
        # Return an error response but with correct content type for SSE
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        }
        
        # Create a simple generator to return error and close
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream not found', 'code': 404, 'error': True})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers=headers
        )
    
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
        realtime_stream_events(queue_id),
        media_type="text/event-stream",
        headers=headers
    )

async def realtime_stream_events(queue_id: str):
    """
    Asynchronous generator function for real-time SSE streaming.
    This implementation ensures events are delivered immediately.
    
    Args:
        queue_id: Queue ID for this specific request
        
    Yields:
        SSE formatted events with immediate flush commands
    """
    if queue_id not in session_queues:
        # If queue doesn't exist, yield an error event
        yield f"data: {json.dumps({'type': 'error', 'message': 'Stream not found', 'code': 404})}\n\n"
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