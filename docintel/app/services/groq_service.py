import os
import json
import re
import httpx
from typing import Any, Dict, Optional, List
from groq import Groq
from app.utils.logging import log_step, Timer
from app.models.retrieval_decision import RetrievalDecision

class GroqService:
    """Service for interacting with Groq's LLMs."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize the Groq service.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY environment variable)
            model: Groq model to use
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            log_step("Groq Service", "Warning: GROQ_API_KEY not found in environment variables")
        
        self.model = model
        # Create a custom httpx client to avoid proxies issue
        http_client = httpx.Client()
        self.client = Groq(api_key=self.api_key, http_client=http_client) if self.api_key else None
        
    def analyze_retrieval_need(self, message: str, conversation_history: List[Dict[str, str]] = None) -> RetrievalDecision:
        """
        Analyze whether a message requires document retrieval.
        
        Args:
            message: The user message to analyze
            conversation_history: Optional list of previous messages in the conversation
            
        Returns:
            RetrievalDecision object with the decision and reasoning
        """
        with Timer("Groq Retrieval Analysis"):
            if not self.client:
                log_step("Groq Service", "Error: Groq client not initialized, using fallback logic")
                return self._fallback_retrieval_decision(message, conversation_history)
            
            try:
                prompt = self._create_retrieval_prompt(message, conversation_history)
                
                log_step("Groq Service", f"Calling Groq API with model: {self.model}")
                response = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI assistant that analyzes whether a user's message requires retrieving documents to answer. Respond in JSON format with the keys 'should_retrieve', 'confidence', 'reasoning', and 'suggested_queries'."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=self.model,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                log_step("Groq Service", f"Received response from Groq: {content[:100]}...")
                
                # Try to parse JSON response
                try:
                    decision_data = json.loads(content)
                    decision = RetrievalDecision(**decision_data)
                    log_step("Groq Service", f"Decision: should_retrieve={decision.should_retrieve}, confidence={decision.confidence}")
                    return decision
                except Exception as e:
                    log_step("Groq Service", f"Error parsing Groq response as JSON: {str(e)}")
                    # Try to extract values using regex or other methods if needed
                    return self._extract_decision_from_text(content)
            except Exception as e:
                log_step("Groq Service Error", f"Error calling Groq API: {str(e)}")
                return self._fallback_retrieval_decision(message, conversation_history)
    
    def _create_retrieval_prompt(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Create a prompt for the retrieval decision."""
        # Format conversation history if provided
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            conversation_context = "Previous conversation:\n"
            for idx, msg in enumerate(conversation_history):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                conversation_context += f"{role.capitalize()}: {content}\n"
            conversation_context += "\nCurrent message: " + message
        else:
            conversation_context = "User message: \"" + message + "\""
        
        prompt = f"""
Analyze the user message and conversation context below to determine if it requires retrieving documents to provide a good answer.

{conversation_context}

Respond with a JSON object with these fields:
- should_retrieve (boolean): Whether documents should be retrieved to answer this query
- confidence (float between 0-1): Your confidence in this decision
- reasoning (string): Your reasoning for the decision
- suggested_queries (array of strings): If should_retrieve is true, provide 1-3 suggested search queries that would best find the relevant information

Criteria for retrieval:
- Factual questions likely benefit from retrieval
- Questions about specific entities, events, or concepts need retrieval
- Conversational or opinion-based messages typically don't need retrieval
- Brief follow-up questions that refer to previous queries may need retrieval with expanded search terms
- If the message is a follow-up to a previous question, consider the entire conversation context when deciding and forming search queries

Response format example:
{{
"should_retrieve": true,
"confidence": 0.85,
"reasoning": "This is a factual question about a specific topic that would benefit from document retrieval",
"suggested_queries": ["query 1", "query 2"]
}}

ONLY output valid JSON.
"""
        return prompt
    
    def _extract_decision_from_text(self, text: str) -> RetrievalDecision:
        """Extract decision components from text if JSON parsing fails."""
        log_step("Groq Service", "Extracting decision from text fallback")
        
        # Try to extract boolean decision
        should_retrieve = False
        if re.search(r"should_retrieve['\"]?\s*:\s*true", text, re.IGNORECASE):
            should_retrieve = True
        
        # Try to extract confidence
        confidence_match = re.search(r"confidence['\"]?\s*:\s*(0\.\d+)", text)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        
        # Try to extract reasoning
        reasoning_match = re.search(r"reasoning['\"]?\s*:\s*['\"]([^'\"]+)['\"]", text)
        reasoning = reasoning_match.group(1) if reasoning_match else "Extracted from malformed response"
        
        # Try to extract suggested queries
        suggested_queries = []
        queries_section = re.search(r"suggested_queries['\"]?\s*:\s*\[(.*?)\]", text, re.DOTALL)
        if queries_section:
            query_matches = re.findall(r"['\"]([^'\"]+)['\"]", queries_section.group(1))
            suggested_queries = query_matches if query_matches else []
        
        return RetrievalDecision(
            should_retrieve=should_retrieve,
            confidence=confidence,
            reasoning=reasoning,
            suggested_queries=suggested_queries
        )
    
    def _fallback_retrieval_decision(self, message: str, conversation_history: List[Dict[str, str]] = None) -> RetrievalDecision:
        """Provide a fallback decision when Groq is unavailable."""
        # Check if this is a follow-up question
        is_follow_up = False
        expanded_query = message
        
        if conversation_history and len(conversation_history) > 0:
            # Get the last user message before the current one
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    previous_query = msg.get("content", "")
                    # If current message is very short and previous is longer, likely a follow-up
                    if len(message.split()) <= 5 and len(previous_query.split()) > 5:
                        is_follow_up = True
                        # Combine previous query with current for context
                        expanded_query = previous_query + " " + message
                    break
        
        # Simple heuristic based on question indicators
        message_lower = expanded_query.lower()
        question_indicators = ["?", "what", "how", "when", "where", "why", "who", "which", "tell me", "explain"]
        contains_question = any(indicator in message_lower for indicator in question_indicators)
        is_long_enough = len(message.split()) >= 3 or is_follow_up
        should_retrieve = contains_question and is_long_enough
        
        suggested_queries = None
        if should_retrieve:
            if is_follow_up:
                suggested_queries = [expanded_query]
            else:
                suggested_queries = [message]
        
        return RetrievalDecision(
            should_retrieve=should_retrieve,
            confidence=0.7 if contains_question else 0.5,
            reasoning="Fallback decision based on question indicators and message length" + 
                    (" (recognized as follow-up question)" if is_follow_up else ""),
            suggested_queries=suggested_queries
        )