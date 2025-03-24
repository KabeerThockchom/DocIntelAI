import os
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
from app.embeddings.embedder import AzureOpenAIEmbedder
from app.storage.chroma_db import ChromaDBStorage
from app.utils.logging import log_step, Timer
from fastapi import Request
import contextvars

# Initialize the embedder
embedder = AzureOpenAIEmbedder()

# Context variable to store the current user ID during async operations
current_user_id = contextvars.ContextVar('current_user_id', default=None)

def get_dummy_chunk(text: str) -> Any:
    """
    Create a dummy document chunk for embedding generation.
    
    Args:
        text: Text to embed
        
    Returns:
        Dummy document chunk
    """
    # Import here to avoid circular import
    from app.chunking.models import DocumentChunk
    
    return DocumentChunk(
        text=text,
        metadata={},
        source_document_id="query",
        source_document_name="query",
        source_document_type="query"
    )

def get_user_storage(user_id: Optional[str] = None):
    """Get ChromaDB storage for the specified user."""
    return ChromaDBStorage(user_id=user_id)

async def retrieve_relevant_chunks_async(
    query: str, 
    filter_criteria: Optional[Dict[str, Any]] = None, 
    top_k: int = 10,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant chunks for a query asynchronously.
    
    Args:
        query: The query text
        filter_criteria: Optional filters
        top_k: Number of chunks to retrieve
        user_id: Optional user ID for collection selection
        
    Returns:
        List of relevant chunks with metadata
    """
    with Timer("Retrieve Chunks Async"):
        log_step("RAG", f"Retrieving chunks asynchronously for query: {query[:50]}...")
        
        # Store the user ID in the context variable
        token = current_user_id.set(user_id)
        
        try:
            # Generate embedding for query asynchronously
            dummy_chunk = get_dummy_chunk(query)
            query_embeddings = await embedder.generate_embeddings_async([dummy_chunk])
            
            if not query_embeddings:
                log_step("RAG", "Failed to generate query embedding", level="error")
                return []
            
            query_embedding = list(query_embeddings.values())[0]
            
            # Get the ChromaDB storage for this user
            chroma_db = get_user_storage(user_id)
            
            # Retrieve more chunks than needed for diversity
            # Use a thread to run the synchronous chroma_db.query_similar
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: chroma_db.query_similar(
                    query_text=query,
                    embedding=query_embedding,
                    n_results=top_k * 2,  # Get more results for post-processing
                    filter_criteria=filter_criteria
                )
            )
            
            # Apply post-processing to improve retrieval quality
            # Run post-processing in a separate thread to avoid blocking
            processed_results = await loop.run_in_executor(
                None,
                lambda: _post_process_results(query, results, top_k)
            )
            
            log_step("RAG", f"Retrieved {len(processed_results)} chunks asynchronously")
            return processed_results
        finally:
            # Reset the context variable
            current_user_id.reset(token)

def retrieve_relevant_chunks(
    query: str, 
    filter_criteria: Optional[Dict[str, Any]] = None, 
    top_k: int = 10,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant chunks for a query.
    
    Args:
        query: The query text
        filter_criteria: Optional filters
        top_k: Number of chunks to retrieve
        user_id: Optional user ID for collection selection
        
    Returns:
        List of relevant chunks with metadata
    """
    with Timer("Retrieve Chunks"):
        log_step("RAG", f"Retrieving chunks for query: {query[:50]}...")
        
        # Generate embedding for query
        query_embeddings = embedder.generate_embeddings([get_dummy_chunk(query)])
        
        if not query_embeddings:
            log_step("RAG", "Failed to generate query embedding", level="error")
            return []
        
        query_embedding = list(query_embeddings.values())[0]
        
        # Get the ChromaDB storage for this user
        chroma_db = get_user_storage(user_id)
        
        # Retrieve more chunks than needed for diversity
        results = chroma_db.query_similar(
            query_text=query,
            embedding=query_embedding,
            n_results=top_k * 2,  # Get more results for post-processing
            filter_criteria=filter_criteria
        )
        
        # Apply post-processing to improve retrieval quality
        processed_results = _post_process_results(query, results, top_k)
        
        log_step("RAG", f"Retrieved {len(processed_results)} chunks")
        return processed_results

def _post_process_results(query: str, results: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """
    Post-process retrieval results to improve quality and diversity.
    
    Args:
        query: The query text
        results: The raw retrieval results
        top_k: Number of results to return
        
    Returns:
        Processed results
    """
    # If not enough results, return what we have
    if len(results) <= top_k:
        return results
    
    # Group results by document to ensure diversity
    doc_groups = {}
    for result in results:
        doc_id = result["metadata"]["source_document_id"]
        if doc_id not in doc_groups:
            doc_groups[doc_id] = []
        doc_groups[doc_id].append(result)
    
    # Sort each group by relevance (lower distance is better)
    for doc_id in doc_groups:
        doc_groups[doc_id].sort(key=lambda x: x.get("distance", 1.0))
    
    # Round-robin selection from each document group to ensure diversity
    final_results = []
    while len(final_results) < top_k and any(doc_groups.values()):
        for doc_id in list(doc_groups.keys()):
            if doc_groups[doc_id]:
                final_results.append(doc_groups[doc_id].pop(0))
                if len(final_results) >= top_k:
                    break
            else:
                del doc_groups[doc_id]
    
    # Ensure results are ordered by relevance
    final_results.sort(key=lambda x: x.get("distance", 1.0))
    
    return final_results[:top_k]

async def retrieve_relevant_chunks_for_multiple_queries(
    queries: List[str], 
    filter_criteria: Optional[Dict[str, Any]] = None, 
    top_k: int = 10,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant chunks for multiple queries and merge the results.
    
    Args:
        queries: List of query texts
        filter_criteria: Optional filters
        top_k: Number of chunks to retrieve per query
        user_id: Optional user ID for collection selection
        
    Returns:
        List of relevant chunks with metadata, with duplicates removed
    """
    with Timer("Retrieve Chunks for Multiple Queries"):
        log_step("RAG", f"Retrieving chunks for {len(queries)} queries...")
        
        # Create tasks for each query
        tasks = []
        for query in queries:
            task = retrieve_relevant_chunks_async(
                query=query,
                filter_criteria=filter_criteria,
                top_k=top_k,
                user_id=user_id
            )
            tasks.append(task)
        
        # Run all tasks in parallel
        results_list = await asyncio.gather(*tasks)
        
        # Merge results, removing duplicates
        merged_results = []
        seen_chunk_ids = set()
        
        for results in results_list:
            for chunk in results:
                chunk_id = chunk["chunk_id"]
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    merged_results.append(chunk)
        
        # Calculate dynamic limit based on number of queries
        # For multiple queries, we want to ensure each query gets fair representation
        dynamic_limit = min(max(top_k * 2, len(queries) * 5), 30)  # Between 2x top_k and 30
        
        # Limit to dynamic_limit results if we have more
        if len(merged_results) > dynamic_limit:
            # Sort by relevance (lower distance is better)
            merged_results.sort(key=lambda x: x.get("distance", 1.0))
            merged_results = merged_results[:dynamic_limit]
        
        log_step("RAG", f"Retrieved {len(merged_results)} unique chunks from {len(queries)} queries")
        return merged_results