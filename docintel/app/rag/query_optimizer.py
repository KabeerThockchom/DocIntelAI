import os
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from app.utils.logging import log_step, Timer
from app.utils.openai_client import create_azure_openai_client

# Initialize Azure OpenAI client
azure_openai_client = create_azure_openai_client()

def optimize_query(query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Optimize a query for better retrieval by expanding it or making it more specific.
    
    Args:
        query: The original query
        chat_history: Optional chat history for context
        
    Returns:
        Optimized query
    """
    with Timer("Query Optimization"):
        log_step("RAG", f"Optimizing query: {query[:50]}...")
        
        # Use Azure OpenAI to rewrite the query
        messages = []
        
        # Add system prompt
        messages.append({
            "role": "system",
            "content": (
                "You are a query optimization assistant. Your job is to rewrite search queries to make them more effective "
                "for semantic search. Focus on extracting key concepts and details that would help retrieve relevant information. "
                "Do not add new information that is not implied by the query or conversation history."
            )
        })
        
        # Add chat history for context if available
        if chat_history:
            # Create a summary of the chat history for context
            history_summary = "\n".join([
                f"{msg['role']}: {msg['content'][:100]}..." if len(msg['content']) > 100 else f"{msg['role']}: {msg['content']}"
                for msg in chat_history[-3:]  # Use last 3 messages for context
            ])
            
            messages.append({
                "role": "user",
                "content": f"Here is the recent conversation history for context:\n{history_summary}"
            })
            
            messages.append({
                "role": "assistant",
                "content": "I'll consider this context when optimizing the search query."
            })
        
        # Add the query optimization instruction
        messages.append({
            "role": "user",
            "content": (
                f"Please rewrite this query to be more effective for semantic search. Make it more specific and "
                f"include key terms that would help retrieve relevant information. Return only the rewritten query "
                f"without explanations or additional text.\n\nOriginal query: {query}"
            )
        })
        
        # Get the optimized query from Azure OpenAI
        response = azure_openai_client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
            messages=messages,
            temperature=0.1,  # Low temperature for more focused results
            max_tokens=150
        )
        
        optimized_query = response.choices[0].message.content.strip()
        
        log_step("RAG", f"Original query: '{query}' → Optimized: '{optimized_query}'")
        return optimized_query

def split_query_into_subqueries(query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> List[str]:
    """
    Split a complex query into multiple sub-queries that cover different topics.
    
    Args:
        query: The original query
        chat_history: Optional chat history for context
        
    Returns:
        List of sub-queries
    """
    with Timer("Query Splitting"):
        log_step("RAG", f"Splitting query into sub-queries: {query[:50]}...")
        
        # Use Azure OpenAI to split the query
        messages = []
        
        # Add system prompt
        messages.append({
            "role": "system",
            "content": (
                "You are a query analysis assistant. Your job is to analyze complex queries and split them into "
                "multiple focused sub-queries that cover different aspects or topics in the original query. "
                "This helps improve retrieval by ensuring each important concept gets proper attention. "
                "For simple queries with a single focus, return just one query. For complex multi-part queries, "
                "split them appropriately.\n\n"
                "IMPORTANT: When a query contains multiple distinct questions or topics (e.g., 'Who is Real Madrid's top scorer and what is their anthem name?'), "
                "you MUST split it into separate sub-queries (e.g., 'Real Madrid top scorer', 'Real Madrid anthem name'). "
                "For each concept, generate multiple variations of the query to increase retrieval coverage. "
                "For example, for 'Real Madrid top scorer', also include 'highest goal scorer Real Madrid', 'leading goalscorer Real Madrid', etc."
            )
        })
        
        # Add chat history for context if available
        if chat_history:
            # Create a summary of the chat history for context
            history_summary = "\n".join([
                f"{msg['role']}: {msg['content'][:100]}..." if len(msg['content']) > 100 else f"{msg['role']}: {msg['content']}"
                for msg in chat_history[-3:]  # Use last 3 messages for context
            ])
            
            messages.append({
                "role": "user",
                "content": f"Here is the recent conversation history for context:\n{history_summary}"
            })
            
            messages.append({
                "role": "assistant",
                "content": "I'll consider this context when analyzing the query."
            })
        
        # Add the query splitting instruction
        messages.append({
            "role": "user",
            "content": (
                f"Please analyze this query and split it into multiple focused sub-queries that cover different aspects "
                f"or topics in the original query. If the query is simple with a single focus, return just one query. "
                f"Format your response as a JSON object with a 'sub_queries' array, where each item is a sub-query string. "
                f"For example: {{\"sub_queries\": [\"sub-query 1\", \"sub-query 2\", ...]}}\n\n"
                f"Original query: {query}"
            )
        })
        
        # Get the sub-queries from Azure OpenAI
        response = azure_openai_client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
            messages=messages,
            temperature=0.1,  # Low temperature for more focused results
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        try:
            import json
            result = json.loads(response.choices[0].message.content.strip())
            
            # Try different possible formats the model might return
            sub_queries = []
            if "sub_queries" in result:
                sub_queries = result["sub_queries"]
            elif "queries" in result:
                sub_queries = result["queries"]
            elif "subQueries" in result:
                sub_queries = result["subQueries"]
            # If it's a direct array at the top level (though this shouldn't happen with response_format=json_object)
            elif isinstance(result, list):
                sub_queries = result
            
            # If no sub-queries were returned or the format is incorrect, use the original query
            if not isinstance(sub_queries, list) or not sub_queries:
                log_step("RAG", "Failed to split query, using original query", level="warning")
                return [optimize_query(query, chat_history)]
            
            # Optimize each sub-query
            optimized_sub_queries = []
            for sub_query in sub_queries:
                optimized_sub_query = optimize_query(sub_query, chat_history)
                optimized_sub_queries.append(optimized_sub_query)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_sub_queries = []
            for sq in optimized_sub_queries:
                if sq.lower() not in seen:
                    seen.add(sq.lower())
                    unique_sub_queries.append(sq)
            
            log_step("RAG", f"Split query into {len(unique_sub_queries)} sub-queries")
            return unique_sub_queries
            
        except Exception as e:
            log_step("RAG", f"Error splitting query: {str(e)}", level="error")
            # Fall back to the original query optimization
            return [optimize_query(query, chat_history)]