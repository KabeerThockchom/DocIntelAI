import os
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from app.utils.logging import log_step, Timer
from app.utils.openai_client import create_azure_openai_client
import json

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
    Split a complex query into multiple targeted sub-queries to improve retrieval.
    
    Args:
        query: The input query to split
        chat_history: Optional chat history for context
        
    Returns:
        List of sub-queries
    """
    try:
        log_step("RAG", f"Splitting query: {query}")
        
        # NOTE: Removed the check for short queries to ensure all queries go through splitting
        # Even if the query is short, we'll let the LLM decide how to handle it
        
        # Create system prompt
        system = {
            "role": "system",
            "content": (
                "You are a helpful assistant that breaks down complex questions into simpler sub-questions for search purposes. "
                "Your job is to analyze a user's question and split it into smaller, focused sub-questions that would help "
                "retrieve relevant information from a document database."
                "\n\n"
                "Rules for creating sub-questions:"
                "\n1. Split complex questions into 1-5 simpler components that help with information retrieval."
                "\n2. Each sub-question should be self-contained, directly answerable, and less than 15 words."
                "\n3. Maintain the original intent and keywords from the user's question."
                "\n4. Don't add interpretations or assumptions not present in the original question."
                "\n5. For simple questions, create at least 2 related sub-questions that explore the topic."
                "\n6. Focus on factual queries, not opinionated aspects."
                "\n7. Preserve named entities, technical terms, and specific references."
                "\n8. Ensure sub-questions collectively cover all aspects of the original question."
                "\n\n"
                "Format your response as a JSON object with a 'sub_queries' array containing the list of sub-questions."
            )
        }
        
        # Create user message
        user = {
            "role": "user",
            "content": f"Split this question into simple sub-questions for effective document search and return them as a JSON array: \"{query}\""
        }
        
        # Add chat history if provided
        messages = [system]
        if chat_history and len(chat_history) > 0:
            # Add a message explaining the history
            messages.append({
                "role": "user",
                "content": "For context, here is the recent conversation history:"
            })
            
            # Add up to 3 most recent exchanges
            recent_history = chat_history[-min(len(chat_history), 6):]
            for msg in recent_history:
                messages.append(msg)
            
            # Then add the actual user query
            messages.append(user)
        else:
            messages.append(user)
            
        try:
            # First attempt with JSON response format
            log_step("RAG", "Attempting query splitting with JSON response format")
            response = azure_openai_client.chat.completions.create(
                model=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"},
                top_p=0.95
            )
            
            # Process the response
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            result = json.loads(response_text)
        except Exception as e:
            # If JSON response format fails, fall back to plain text
            log_step("RAG", f"JSON response format failed: {str(e)}. Falling back to plain text.", level="warning")
            
            # Modify system prompt to request newline-separated format
            fallback_system = {
                "role": "system",
                "content": (
                    "You are a helpful assistant that breaks down complex questions into simpler sub-questions for search purposes. "
                    "Your job is to analyze a user's question and split it into smaller, focused sub-questions that would help "
                    "retrieve relevant information from a document database."
                    "\n\n"
                    "Rules for creating sub-questions:"
                    "\n1. Split complex questions into 1-5 simpler components that help with information retrieval."
                    "\n2. Each sub-question should be self-contained, directly answerable, and less than 15 words."
                    "\n3. Maintain the original intent and keywords from the user's question."
                    "\n4. Don't add interpretations or assumptions not present in the original question."
                    "\n5. For simple questions, create at least 2 related sub-questions that explore the topic."
                    "\n6. Focus on factual queries, not opinionated aspects."
                    "\n7. Preserve named entities, technical terms, and specific references."
                    "\n8. Ensure sub-questions collectively cover all aspects of the original question."
                    "\n\n"
                    "Format your response as a simple list with one sub-question per line. No numbering or extra text."
                )
            }
            
            # Create fallback user message
            fallback_user = {
                "role": "user",
                "content": f"Split this question into simple sub-questions for search, one per line: \"{query}\""
            }
            
            # Try the fallback approach
            try:
                fallback_messages = [fallback_system, fallback_user]
                response = azure_openai_client.chat.completions.create(
                    model=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
                    messages=fallback_messages,
                    temperature=0.2,
                    max_tokens=1024,
                    top_p=0.95
                )
                
                # Process the response as a simple list
                response_text = response.choices[0].message.content
                
                # Split by newlines and filter out empty lines
                sub_queries = [line.strip() for line in response_text.split('\n') if line.strip()]
                
                # Create a result dictionary to match the expected format
                result = {"sub_queries": sub_queries}
                
            except Exception as fallback_error:
                log_step("RAG", f"Fallback approach also failed: {str(fallback_error)}. Using original query.", level="error")
                return [query]
        
        # Extract sub-queries from various possible formats
        sub_queries = []
        if "sub_queries" in result:
            sub_queries = result["sub_queries"]
        elif "subQueries" in result:
            sub_queries = result["subQueries"]
        # If it's a direct array at the top level (though this shouldn't happen with response_format=json_object)
        elif isinstance(result, list):
            sub_queries = result
        
        # If no sub-queries were returned or the format is incorrect, use the original query
        if not isinstance(sub_queries, list) or not sub_queries:
            log_step("RAG", "Failed to split query, using original query", level="warning")
            return [query]
        
        # Ensure we have at least 2 sub-queries
        if len(sub_queries) < 2:
            # If only one sub-query and it's identical to the original query, create a simple variation
            if len(sub_queries) == 1 and sub_queries[0].lower().strip() == query.lower().strip():
                sub_queries.append(f"Information about {query.strip()}")
            # If empty, use the original query plus a variation
            elif len(sub_queries) == 0:
                sub_queries = [query, f"Information about {query.strip()}"]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_sub_queries = []
        for sq in sub_queries:
            if sq and sq.lower() not in seen:
                seen.add(sq.lower())
                unique_sub_queries.append(sq)
        
        # Make sure we have at least one query
        if not unique_sub_queries:
            unique_sub_queries = [query]
        
        log_step("RAG", f"Split query into {len(unique_sub_queries)} sub-queries")
        return unique_sub_queries
        
    except Exception as e:
        log_step("RAG", f"Error splitting query: {str(e)}", level="error")
        # Fall back to the original query
        return [query]