import os
import logging
import asyncio
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
import httpx
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from app.chunking.models import DocumentChunk
from app.utils.logging import log_step, Timer


async def get_embeddings_async(texts: List[str], deployment_name: str = "text-embedding-ada-002") -> List[List[float]]:
    """
    Get embeddings for a batch of texts using Azure OpenAI asynchronously.
    
    Args:
        texts: List of texts to embed
        deployment_name: Azure OpenAI deployment name for embeddings
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
        
    try:
        # Get API credentials from environment
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("ENDPOINT_URL", "https://eyvoicecentralus.openai.azure.com/")
        api_version = os.getenv("AZURE_API_VERSION", "2024-05-01-preview")
        
        # Initialize Azure OpenAI client with custom http_client to avoid proxies issue
        http_client = httpx.Client()
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
            http_client=http_client
        )
        
        # Process in larger batches to take advantage of high rate limits
        # Increased from 20 to 100 based on the 20,000 requests per minute limit
        batch_size = 100
        
        # Create batches
        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        
        # Process batches in parallel
        async def process_batch(batch):
            response = client.embeddings.create(
                model=deployment_name,
                input=batch
            )
            return [item.embedding for item in response.data]
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=10) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    executor,
                    lambda b=batch: client.embeddings.create(
                        model=deployment_name,
                        input=b
                    )
                )
                for batch in batches
            ]
            
            # Gather results
            all_embeddings = []
            for future in await asyncio.gather(*tasks):
                batch_embeddings = [item.embedding for item in future.data]
                all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
        
    except Exception as e:
        log_step("Embedding Error", f"Error generating embeddings: {str(e)}", level="error")
        raise


def get_embeddings(texts: List[str], deployment_name: str = "text-embedding-ada-002") -> List[List[float]]:
    """
    Get embeddings for a batch of texts using Azure OpenAI.
    
    Args:
        texts: List of texts to embed
        deployment_name: Azure OpenAI deployment name for embeddings
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
        
    try:
        # Get API credentials from environment
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("ENDPOINT_URL", "https://eyvoicecentralus.openai.azure.com/")
        api_version = os.getenv("AZURE_API_VERSION", "2024-05-01-preview")
        
        # Initialize Azure OpenAI client with custom http_client to avoid proxies issue
        http_client = httpx.Client()
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
            http_client=http_client
        )
        
        # Process in larger batches to take advantage of high rate limits
        # Increased from 20 to 100 based on the 20,000 requests per minute limit
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            response = client.embeddings.create(
                model=deployment_name,
                input=batch_texts
            )
            
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
        
    except Exception as e:
        log_step("Embedding Error", f"Error generating embeddings: {str(e)}", level="error")
        raise


class AzureOpenAIEmbedder:
    """Generates embeddings using Azure OpenAI's embedding models."""

    def __init__(self, deployment_name: str = "text-embedding-ada-002"):
        self.deployment_name = deployment_name

    async def generate_embeddings_async(self, chunks: List[DocumentChunk]) -> Dict[str, List[float]]:
        """
        Generate embeddings for a list of document chunks asynchronously.

        Args:
            chunks: List of document chunks

        Returns:
            Dictionary mapping chunk IDs to embeddings
        """
        embeddings = {}

        if not chunks:
            log_step("Embedding Generation", "No chunks to embed")
            return embeddings

        try:
            # Extract texts from chunks
            texts = [chunk.text for chunk in chunks]

            # Get embeddings from Azure OpenAI
            if texts:
                log_step("Embedding Generation", f"Generating embeddings for {len(texts)} chunks asynchronously")
                embedding_vectors = await get_embeddings_async(texts, self.deployment_name)

                # Map chunk IDs to embeddings
                for i, chunk in enumerate(chunks):
                    if i < len(embedding_vectors):
                        embeddings[chunk.chunk_id] = embedding_vectors[i]

            log_step("Embedding Generation", f"Generated {len(embeddings)} embeddings asynchronously")
            return embeddings
        except Exception as e:
            log_step("Embedding Error", f"Error generating embeddings asynchronously: {str(e)}")
            return embeddings

    def generate_embeddings(self, chunks: List[DocumentChunk]) -> Dict[str, List[float]]:
        """
        Generate embeddings for a list of document chunks.

        Args:
            chunks: List of document chunks

        Returns:
            Dictionary mapping chunk IDs to embeddings
        """
        embeddings = {}

        if not chunks:
            log_step("Embedding Generation", "No chunks to embed")
            return embeddings

        try:
            # Extract texts from chunks
            texts = [chunk.text for chunk in chunks]

            # Get embeddings from Azure OpenAI
            if texts:
                log_step("Embedding Generation", f"Generating embeddings for {len(texts)} chunks")
                embedding_vectors = get_embeddings(texts, self.deployment_name)

                # Map chunk IDs to embeddings
                for i, chunk in enumerate(chunks):
                    if i < len(embedding_vectors):
                        embeddings[chunk.chunk_id] = embedding_vectors[i]

            log_step("Embedding Generation", f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            log_step("Embedding Error", f"Error generating embeddings: {str(e)}")
            return embeddings