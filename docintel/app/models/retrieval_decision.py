from typing import List, Optional
from pydantic import BaseModel, Field

class RetrievalDecision(BaseModel):
    """Model for representing a decision about whether to retrieve documents."""
    
    should_retrieve: bool = Field(
        description="Whether documents should be retrieved to answer the query"
    )
    
    confidence: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Confidence level in the decision (0.0 to 1.0)"
    )
    
    reasoning: str = Field(
        description="Explanation for why this decision was made"
    )
    
    suggested_queries: Optional[List[str]] = Field(
        default=None,
        description="List of suggested search queries if retrieval is needed"
    )