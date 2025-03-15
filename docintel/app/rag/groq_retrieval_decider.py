from typing import List, Dict, Any, Optional
import os
from app.services.groq_service import GroqService
from app.models.retrieval_decision import RetrievalDecision
from app.utils.logging import log_step, Timer

# Initialize Groq service
groq_service = GroqService(
    api_key=os.getenv("GROQ_API_KEY"),
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
)

def should_use_retrieval(query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Determine if a query requires document retrieval using Groq's LLM.
    
    Args:
        query: The user query
        chat_history: Optional chat history for context
        
    Returns:
        Dict with decision and reasoning
    """
    with Timer("Groq Retrieval Decision"):
        log_step("RAG", f"Analyzing need for retrieval via Groq: {query[:50]}...")
        
        # Get decision from Groq service
        decision = groq_service.analyze_retrieval_need(query, chat_history)
        
        # Format response to match existing API
        result = {
            "retrieval_needed": decision.should_retrieve,
            "reasoning": decision.reasoning,
            "confidence": decision.confidence,
        }
        
        # Include suggested queries if available
        if decision.suggested_queries:
            result["suggested_queries"] = decision.suggested_queries
            
            # Use the first suggested query for optimization if available
            if decision.should_retrieve and len(decision.suggested_queries) > 0:
                result["optimized_query"] = decision.suggested_queries[0]
        
        log_step("RAG", f"Groq retrieval decision: {result['retrieval_needed']} ({result['confidence']:.2f}) - {result['reasoning']}")
        return result