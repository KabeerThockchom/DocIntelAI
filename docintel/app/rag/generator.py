import os
import re
import asyncio
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
import httpx
from app.utils.logging import log_step, Timer
from concurrent.futures import ThreadPoolExecutor

# Initialize Azure OpenAI client with a custom HTTP client to avoid proxies issue
http_client = httpx.Client()
azure_openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_API_VERSION", "2024-05-01-preview"),
    azure_endpoint=os.getenv("ENDPOINT_URL", "https://eyvoicecentralus.openai.azure.com/"),
    http_client=http_client
)

# Configure thread pool for parallel processing
MAX_WORKERS = 10
thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

def generate_answer(
    query: str, 
    retrieved_chunks: List[Dict[str, Any]], 
    chat_history: Optional[List[Dict[str, str]]] = None,
    max_tokens: int = 4096,  # Increased from 1500 to take advantage of higher limits
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an answer using Azure OpenAI referencing the retrieved chunks.
    Responses are formatted in Markdown for rich text rendering.
    
    Args:
        query: The user's query
        retrieved_chunks: The retrieved context chunks
        chat_history: Optional chat history
        max_tokens: Maximum tokens for the response
        user_id: Optional user ID for user-specific processing
        
    Returns:
        Dict with answer (in Markdown) and citations
    """
    with Timer("Generate Answer"):
        log_step("RAG", f"Generating answer for query: {query[:50]}... (user: {user_id or 'unknown'})")
        
        # Format chunks for context and prepare citation map
        formatted_chunks, citation_map = _prepare_context_and_citations(retrieved_chunks)
        
        # Prepare system prompt
        system_prompt = _get_system_prompt()
        
        # Format chat history if available
        formatted_history = _format_chat_history(chat_history) if chat_history else []
        
        # Prepare final prompt with context, history, and query
        final_prompt = _create_final_prompt(system_prompt, formatted_history, formatted_chunks, query)
        
        # Generate answer using Azure OpenAI
        response = azure_openai_client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
            messages=final_prompt,
            temperature=0.5,
            max_tokens=max_tokens
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Return all citations instead of extracting only the referenced ones
        all_citations = [
            {**citation_data, "citation_id": citation_id} 
            for citation_id, citation_data in citation_map.items()
        ]
        
        log_step("RAG", f"Generated answer with all {len(all_citations)} citations")
        return {
            "answer": answer,
            "citations": all_citations
        }

async def generate_answer_async(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    chat_history: Optional[List[Dict[str, str]]] = None,
    max_tokens: int = 2000,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an answer asynchronously using Azure OpenAI.
    
    Args:
        query: The user's query
        retrieved_chunks: The retrieved context chunks
        chat_history: Optional chat history
        max_tokens: Maximum tokens for the response
        user_id: Optional user ID for user-specific processing
        
    Returns:
        Dict with answer (in Markdown) and citations
    """
    with Timer("Generate Answer Async"):
        log_step("RAG", f"Generating answer asynchronously for query: {query[:50]}... (user: {user_id or 'unknown'})")
        
        # Run preparation steps in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Format chunks for context and prepare citation map
        formatted_chunks, citation_map = await loop.run_in_executor(
            thread_pool,
            lambda: _prepare_context_and_citations(retrieved_chunks)
        )
        
        # Prepare system prompt
        system_prompt = _get_system_prompt()
        
        # Format chat history if available
        formatted_history = await loop.run_in_executor(
            thread_pool,
            lambda: _format_chat_history(chat_history) if chat_history else []
        )
        
        # Prepare final prompt with context, history, and query
        final_prompt = await loop.run_in_executor(
            thread_pool,
            lambda: _create_final_prompt(system_prompt, formatted_history, formatted_chunks, query)
        )
        
        # Generate answer using Azure OpenAI
        response = await loop.run_in_executor(
            thread_pool,
            lambda: azure_openai_client.chat.completions.create(
                model=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
                messages=final_prompt,
                temperature=0.5,
                max_tokens=max_tokens
            )
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Return all citations instead of extracting only the referenced ones
        all_citations = await loop.run_in_executor(
            thread_pool,
            lambda: [
                {**citation_data, "citation_id": citation_id} 
                for citation_id, citation_data in citation_map.items()
            ]
        )
        
        log_step("RAG", f"Generated answer asynchronously with all {len(all_citations)} citations")
        return {
            "answer": answer,
            "citations": all_citations
        }

async def batch_generate_answers(
    queries: List[str],
    retrieved_chunks_list: List[List[Dict[str, Any]]],
    chat_histories: Optional[List[List[Dict[str, str]]]] = None,
    max_tokens: int = 2000,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate answers for multiple queries in parallel.
    
    Args:
        queries: List of user queries
        retrieved_chunks_list: List of retrieved chunks for each query
        chat_histories: Optional list of chat histories for each query
        max_tokens: Maximum tokens for each response
        user_id: Optional user ID for user-specific processing
        
    Returns:
        List of answers with citations
    """
    with Timer(f"Batch Generate {len(queries)} Answers"):
        log_step("RAG", f"Batch generating answers for {len(queries)} queries for user {user_id or 'unknown'}...")
        
        if chat_histories is None:
            chat_histories = [None] * len(queries)
        
        # Create tasks for each query
        tasks = []
        for i, query in enumerate(queries):
            task = generate_answer_async(
                query=query,
                retrieved_chunks=retrieved_chunks_list[i],
                chat_history=chat_histories[i] if i < len(chat_histories) else None,
                max_tokens=max_tokens,
                user_id=user_id
            )
            tasks.append(task)
        
        # Run all tasks in parallel
        results = await asyncio.gather(*tasks)
        
        log_step("RAG", f"Completed batch generation of {len(results)} answers for user {user_id or 'unknown'}")
        return results

def _prepare_context_and_citations(retrieved_chunks: List[Dict[str, Any]]) -> tuple:
    """
    Format chunks for context and prepare citation map.
    
    Args:
        retrieved_chunks: The retrieved context chunks
        
    Returns:
        Tuple of (formatted_chunks, citation_map)
    """
    formatted_chunks = ""
    citation_map = {}
    
    for i, chunk in enumerate(retrieved_chunks):
        citation_id = f"[{i+1}]"
        
        # Extract metadata
        metadata = chunk.get("metadata", {})
        document_name = metadata.get("source_document_name", "Unknown")
        page_info = f", Page {metadata.get('page_number')}" if metadata.get("page_number") is not None else ""
        
        # Format chunk with citation info
        formatted_chunks += (
            f"\n{citation_id} From: {document_name}{page_info}\n"
            f"{chunk['text']}\n"
        )
        
        # Store citation metadata
        citation_map[citation_id] = {
            "chunk_id": chunk["chunk_id"],
            "document_id": metadata.get("source_document_id", "unknown"),
            "document_name": document_name,
            "page_number": metadata.get("page_number"),
            "bounding_box": metadata.get("bounding_box"),
            "text_snippet": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
            "relevance_score": 1.0 - chunk.get("distance", 0)
        }
    
    return formatted_chunks, citation_map

def _get_system_prompt() -> Dict[str, str]:
    """
    Get the system prompt for the LLM.
    
    Returns:
        System prompt message
    """
    return {
        "role": "system",
        "content": (
            "You are an intelligent assistant that provides accurate, helpful responses based on the provided context and conversation history. "
            "You MUST pay careful attention to the conversation history when answering follow-up questions. "
            "\n\n"
            "CRITICAL INSTRUCTION: When the user asks questions like 'what did I just say?', 'what was my previous message?', "
            "or similar self-referential questions about the conversation, you MUST respond by quoting their most recent previous "
            "message from the conversation history - NOT the current question they're asking.\n\n"
            "For example, if the conversation history shows the user said 'Tell me about Apple revenue' and then asks 'What did I just say?', "
            "your response should be: 'You just said: \"Tell me about Apple revenue\"'\n\n"
            "Format your responses using Markdown syntax for better readability. "
            "Follow these guidelines when answering:\n\n"
            
            "## Response Formatting Guidelines\n"
            "1. ALWAYS use information from the provided context when available.\n"
            "2. ALWAYS reference conversation history for follow-up questions.\n"
            "3. When you use information from the context, cite your sources using the citation format provided [1], [2], etc.\n"
            "4. Include the citation immediately after the information it supports, not at the end of paragraphs.\n"
            "5. If multiple sections support the same information, cite all of them [1][3].\n"
            "6. If the context doesn't contain relevant information, check if the question relates to conversation history.\n"
            "7. Never make up information or citations.\n"
            "8. Keep your answers comprehensive but concise.\n"
            "9. When information appears in multiple sources, prioritize the most specific and recent sources.\n"
            "10. Always maintain context of the conversation history when responding.\n\n"
            
            "## Conversation History Guidelines\n"
            "1. When the user asks 'what did I just say?' or similar, respond by directly quoting their previous message not the current question.\n"
            "2. When the user refers to content from earlier in the conversation, acknowledge and use that information.\n"
            "3. Track the topic thread of the conversation to provide coherent and relevant responses.\n"
            "4. If a question is ambiguous, use conversation history to determine what the user is asking about.\n\n"
            
            "## Markdown Formatting\n"
            "1. Use Markdown headings (# ## ###) to organize your answer when appropriate.\n"
            "2. Use **bold** for emphasis on important points.\n"
            "3. Use _italics_ for definitions or secondary emphasis.\n"
            "4. Use `code blocks` for code, technical terms, or specific values.\n"
            "5. Use bullet points or numbered lists for sequences or multiple items.\n"
            "6. Use > blockquotes for direct quotes from the context.\n"
            "7. Use tables for tabular data when appropriate. Format tables properly with headers and alignment:\n"
            "   ```\n"
            "   | Header 1 | Header 2 | Header 3 |\n"
            "   | -------- | -------- | -------- |\n"
            "   | Cell 1   | Cell 2   | Cell 3   |\n"
            "   ```\n"
            "   For column alignment, use colons in the header separator row:\n"
            "   ```\n"
            "   | Left     | Center   | Right    |\n"
            "   | :------- |:--------:| --------:|\n"
            "   | Left     | Center   | Right    |\n"
            "   ```\n"
            "   Each column should have consistent width. Add appropriate spacing for better readability.\n"
            "8. Use triple backticks for code blocks with language specification.\n"
            "9. Make sure citation markers [1] remain separate from Markdown formatting.\n\n"
            
            "The citations refer to specific documents and page numbers, which allows users to verify the information."
        )
    }

def _format_chat_history(chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Format chat history for the LLM prompt.
    
    Args:
        chat_history: List of chat messages
        
    Returns:
        Formatted chat history messages
    """
    # Check if chat history is None or empty
    if not chat_history:
        log_step("RAG", "No chat history provided")
        return []
        
    # Log the original chat history for debugging
    log_step("RAG", f"Original chat history length: {len(chat_history)}")
    for i, msg in enumerate(chat_history[:3]):  # Log first 3 messages to avoid overwhelming logs
        try:
            content_preview = msg.get("content", "")[:30] + "..." if msg.get("content") else "[No content]"
            log_step("RAG", f"  History[{i}]: role={msg.get('role', 'unknown')}, content={content_preview}")
        except Exception as e:
            log_step("RAG", f"  Error logging history[{i}]: {str(e)}", level="warning")
    
    if len(chat_history) > 3:
        log_step("RAG", f"  ... and {len(chat_history) - 3} more messages")
        
    # Limit history to last 10 messages to provide more context while keeping prompt manageable
    recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
    
    # Format as messages
    formatted_history = []
    for message in recent_history:
        # Ensure message has valid role and content
        if isinstance(message, dict) and "role" in message and "content" in message:
            # Check if the role is valid (user or assistant)
            role = message["role"]
            if role not in ["user", "assistant", "system"]:
                # Default to user if role is invalid
                role = "user"
                log_step("RAG", f"Invalid role '{message['role']}' in chat history, defaulting to 'user'")
            
            # Skip empty messages
            if not message["content"] or message["content"].strip() == "":
                log_step("RAG", f"Skipping empty message with role '{role}'", level="warning")
                continue
                
            formatted_history.append({
                "role": role,
                "content": message["content"]
            })
        else:
            # Log error for malformed message
            log_step("RAG", f"Skipping malformed chat history message: {message}", level="warning")
    
    # Debugging - log the formatted history
    log_step("RAG", f"Using {len(formatted_history)} messages from chat history")
    
    return formatted_history

def _create_final_prompt(
    system_prompt: Dict[str, str],
    formatted_history: List[Dict[str, str]],
    formatted_chunks: str,
    query: str
) -> List[Dict[str, str]]:
    """
    Create the final prompt for the LLM.
    
    Args:
        system_prompt: System prompt message
        formatted_history: Formatted chat history
        formatted_chunks: Formatted context chunks
        query: User query
        
    Returns:
        Final prompt messages
    """
    # Start with system prompt
    final_prompt = [system_prompt]
    
    # Add chat history if available
    if formatted_history and len(formatted_history) > 0:
        log_step("RAG", f"Adding {len(formatted_history)} messages from chat history to the prompt")
        
        # Add the chat history as separate messages
        final_prompt.extend(formatted_history)
        
        # Add a "thinking" transition to explicitly mark the separation between history and current query
        final_prompt.append({
            "role": "system",
            "content": "The user has a new question. Remember to consider both the conversation history above and the retrieved context below when formulating your response."
        })
        
        # Add context and query as a new message, separate from the history
        final_prompt.append({
            "role": "user",
            "content": (
                f"User Query: {query}\n\n"
                f"Please use BOTH the context below AND our previous conversation history to provide an accurate answer with proper citations.\n\n"
                f"CONTEXT:\n{formatted_chunks}\n\n"
                f"If the context doesn't contain information relevant to my question, please check if it's a follow-up question referring to our previous conversation. "
                f"For questions like 'What did I just say?' or 'What was my previous message?', use our conversation history to provide the correct answer."
            )
        })
    else:
        # If no history, use standard prompt
        log_step("RAG", "No chat history available, using standard prompt")
        final_prompt.append({
            "role": "user",
            "content": (
                f"I need information on the following topic. Please use the provided context to answer accurately with proper citations. "
                f"Format your response using Markdown for better readability.\n\n"
                f"CONTEXT:\n{formatted_chunks}\n\n"
                f"QUESTION: {query}\n\n"
                f"If the context doesn't contain information relevant to my question, please let me know rather than making something up."
            )
        })
    
    return final_prompt

def _extract_citations(answer: str, citation_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract citations from the answer.
    
    Args:
        answer: Generated answer
        citation_map: Map of citation IDs to metadata
        
    Returns:
        List of citations
    """
    citations = []
    citation_ids = set()
    
    # Look for citations in format [n]
    citation_pattern = r'\[(\d+)\]'
    matches = re.findall(citation_pattern, answer)
    
    for match in matches:
        citation_id = f"[{match}]"
        if citation_id in citation_map and citation_id not in citation_ids:
            citation_ids.add(citation_id)
            citation_data = citation_map[citation_id].copy()
            citation_data["citation_id"] = citation_id
            citations.append(citation_data)
    
    return citations