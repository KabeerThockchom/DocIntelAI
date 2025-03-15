# RAG (Retrieval Augmented Generation) Package
"""
Retrieval and generation components for document-based question answering.
"""

from app.rag.query_optimizer import optimize_query
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.generator import generate_answer
from app.rag.groq_retrieval_decider import should_use_retrieval