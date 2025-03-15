import os
from typing import List, Dict, Any, Optional, Union
import json
import chromadb
from chromadb.config import Settings
from app.chunking.models import DocumentChunk, ProcessedDocument
from app.utils.logging import log_step, Timer


class ChromaDBStorage:
    """Storage for document chunks and embeddings using Chroma DB."""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB storage.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with proper persistence settings
        self.client = chromadb.PersistentClient(
            path=persist_directory
        )
        
        # Create collections if they don't exist
        self.documents_collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def store_document(
        self, 
        document: ProcessedDocument,
        embeddings: Dict[str, List[float]]
    ) -> str:
        """
        Store a processed document with embeddings.
        
        Args:
            document: Processed document with chunks
            embeddings: Dictionary mapping chunk IDs to embeddings
            
        Returns:
            Document ID
        """
        with Timer("Chroma DB Storage"):
            log_step("Storage", f"Storing document: {document.filename}")
            
            # Prepare data for storage
            ids = []
            embedding_vectors = []
            metadatas = []
            documents = []
            
            # Track document-level statistics
            ocr_chunk_count = 0
            
            # Extract file path from the first chunk's metadata if available
            file_path = None
            if document.chunks and hasattr(document.chunks[0], 'metadata'):
                file_path = document.chunks[0].metadata.get('file_path')
            
            for chunk in document.chunks:
                # Skip chunks without embeddings
                if chunk.chunk_id not in embeddings:
                    log_step("Storage", f"Skipping chunk {chunk.chunk_id} - no embedding", level="warning")
                    continue
                
                # Count OCR chunks
                if chunk.is_ocr:
                    ocr_chunk_count += 1
                
                # Add chunk data
                ids.append(chunk.chunk_id)
                embedding_vectors.append(embeddings[chunk.chunk_id])
                
                # Prepare metadata (must be JSON serializable)
                metadata = {
                    "source_document_id": chunk.source_document_id,
                    "source_document_name": chunk.source_document_name,
                    "source_document_type": chunk.source_document_type,
                    "page_number": chunk.page_number if chunk.page_number is not None else -1,
                    "is_ocr": chunk.is_ocr,
                    "created_at": chunk.created_at.isoformat(),
                    "is_document_metadata": False  # Explicitly mark as not metadata
                }
                
                # Add optional metadata if available
                if chunk.heading_path:
                    metadata["heading_path"] = json.dumps(chunk.heading_path)
                if chunk.heading_level is not None:
                    metadata["heading_level"] = chunk.heading_level
                if chunk.bounding_box:
                    metadata["bounding_box"] = json.dumps(chunk.bounding_box)
                
                # Add any additional metadata from the chunk
                for key, value in chunk.metadata.items():
                    if key not in metadata and isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                    elif isinstance(value, list) or isinstance(value, dict):
                        metadata[key] = json.dumps(value)
                
                metadatas.append(metadata)
                documents.append(chunk.text)
            
            # Add data to collection
            if ids:
                self.documents_collection.add(
                    ids=ids,
                    embeddings=embedding_vectors,
                    metadatas=metadatas,
                    documents=documents
                )
                
                log_step("Storage", f"Stored {len(ids)} chunks for document {document.document_id}")
                
            # Store document-level metadata in a separate collection or as a special chunk
            # This enables us to efficiently query document metadata without retrieving all chunks
            document_metadata = {
                "document_id": document.document_id,
                "filename": document.filename,
                "document_type": document.file_type,
                "file_size": document.file_size,
                "total_pages": document.total_pages,
                "chunk_count": len(document.chunks),
                "ocr_chunk_count": ocr_chunk_count,
                "ocr_used": document.is_complex or ocr_chunk_count > 0,
                "processing_time": document.processing_time,
                "created_at": document.created_at.isoformat(),
            }
            
            # Add file path to document metadata if available
            if file_path:
                document_metadata["file_path"] = file_path
            
            # Check if file_path exists in any chunk's metadata
            for chunk in document.chunks:
                if hasattr(chunk, 'metadata') and 'file_path' in chunk.metadata:
                    document_metadata["file_path"] = chunk.metadata['file_path']
                    break
            
            # Add document metadata as a special chunk with a distinct prefix
            doc_meta_id = f"DOC_META_{document.document_id}"
            
            # Create metadata for the document metadata chunk
            doc_meta_metadata = {
                "is_document_metadata": True,
                "source_document_id": document.document_id,
                "source_document_name": document.filename,
                "source_document_type": document.file_type,
                "document_metadata": json.dumps(document_metadata)
            }
            
            # Add file_path directly to the metadata for easier access
            if "file_path" in document_metadata:
                doc_meta_metadata["file_path"] = document_metadata["file_path"]
            
            self.documents_collection.add(
                ids=[doc_meta_id],
                embeddings=[[0.0] * 1536],  # Dummy embedding (never retrieved by similarity)
                metadatas=[doc_meta_metadata],
                documents=[f"Document metadata for {document.filename}"]
            )
                
            return document.document_id
    
    def query_similar(
        self, 
        query_text: str,
        embedding: List[float],
        n_results: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for chunks similar to a query text.
        
        Args:
            query_text: Query text
            embedding: Query embedding vector
            n_results: Number of results to return
            filter_criteria: Filter criteria for metadata
            
        Returns:
            List of similar chunks with metadata
        """
        with Timer("Chroma DB Query"):
            log_step("Query", f"Querying for: {query_text[:50]}...")
            
            # Prepare filter structure
            if filter_criteria:
                # If we have additional criteria, use $and
                where_filter = {
                    "$and": [
                        {"is_document_metadata": {"$eq": False}},
                        # Add additional filter criteria
                        *[{key: {"$eq": value}} for key, value in filter_criteria.items()]
                    ]
                }
            else:
                # If we only have the is_document_metadata condition, don't use $and
                where_filter = {"is_document_metadata": {"$eq": False}}
            
            # Query collection
            results = self.documents_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where=where_filter
            )
            
            # Format results
            formatted_results = []
            
            if results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    chunk_id = results["ids"][0][i]
                    text = results["documents"][0][i]
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i] if "distances" in results else None
                    
                    # Process metadata
                    processed_metadata = metadata.copy()
                    
                    # Convert JSON strings back to objects
                    if "heading_path" in processed_metadata:
                        processed_metadata["heading_path"] = json.loads(processed_metadata["heading_path"])
                    if "bounding_box" in processed_metadata:
                        processed_metadata["bounding_box"] = json.loads(processed_metadata["bounding_box"])
                    
                    # Add result
                    formatted_results.append({
                        "chunk_id": chunk_id,
                        "text": text,
                        "metadata": processed_metadata,
                        "distance": distance
                    })
            
            log_step("Query", f"Found {len(formatted_results)} results")
            return formatted_results
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its chunks.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete all chunks with this document ID
            self.documents_collection.delete(
                where={"source_document_id": {"$eq": document_id}}
            )
            
            log_step("Storage", f"Deleted document: {document_id}")
            return True
            
        except Exception as e:
            log_step("Storage", f"Error deleting document: {str(e)}", level="error")
            return False
    
    def list_documents(
        self, 
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List all documents in the system.
        
        Args:
            filter_criteria: Filter criteria for documents
            
        Returns:
            List of document metadata
        """
        with Timer("List Documents"):
            try:
                # Prepare filter structure - don't use $and if there's only one condition
                if filter_criteria:
                    # If we have additional criteria, use $and
                    where_filter = {
                        "$and": [
                            {"is_document_metadata": {"$eq": True}},
                            # Add additional filter criteria
                            *[{key: {"$eq": value}} for key, value in filter_criteria.items()]
                        ]
                    }
                else:
                    # If we only have the is_document_metadata condition, don't use $and
                    where_filter = {"is_document_metadata": {"$eq": True}}
                
                # Query collection for document metadata entries
                results = self.documents_collection.get(
                    where=where_filter,
                    include=["metadatas", "documents"]
                )
                
                # Format results
                documents = []
                
                if results["ids"]:
                    for i in range(len(results["ids"])):
                        metadata = results["metadatas"][i]
                        
                        # Parse document metadata
                        if "document_metadata" in metadata:
                            document_metadata = json.loads(metadata["document_metadata"])
                            documents.append(document_metadata)
                
                log_step("Storage", f"Found {len(documents)} documents")
                return documents
                
            except Exception as e:
                log_step("Storage", f"Error listing documents: {str(e)}", level="error")
                return []
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document metadata, or None if not found
        """
        with Timer("Get Document"):
            try:
                # Query using proper filter structure
                where_filter = {
                    "$and": [
                        {"is_document_metadata": {"$eq": True}},
                        {"source_document_id": {"$eq": document_id}}
                    ]
                }
                
                # Query collection for document metadata entry
                results = self.documents_collection.get(
                    where=where_filter,
                    include=["metadatas"]
                )
                
                # Return document metadata if found
                if results["ids"] and len(results["ids"]) > 0:
                    metadata = results["metadatas"][0]
                    
                    # Parse document metadata
                    if "document_metadata" in metadata:
                        document_metadata = json.loads(metadata["document_metadata"])
                        
                        # Add file_path directly from the metadata if available
                        if "file_path" in metadata:
                            document_metadata["file_path"] = metadata["file_path"]
                            
                        # Verify file path exists and is valid
                        if "file_path" in document_metadata:
                            file_path = document_metadata["file_path"]
                            if not os.path.exists(file_path):
                                log_step("Storage", f"Warning: File path {file_path} does not exist", level="warning")
                        else:
                            log_step("Storage", f"Warning: No file path found for document {document_id}", level="warning")
                            
                        return document_metadata
                
                log_step("Storage", f"Document {document_id} not found")
                return None
                
            except Exception as e:
                log_step("Storage", f"Error getting document: {str(e)}", level="error")
                return None
    
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of document chunks
        """
        with Timer("Get Document Chunks"):
            try:
                # Proper filter structure
                where_filter = {
                    "$and": [
                        {"source_document_id": {"$eq": document_id}},
                        {"is_document_metadata": {"$eq": False}}
                    ]
                }
                
                # Query collection for document chunks
                results = self.documents_collection.get(
                    where=where_filter,
                    include=["metadatas", "documents"]
                )
                
                # Format results
                chunks = []
                
                if results["ids"]:
                    for i in range(len(results["ids"])):
                        chunk_id = results["ids"][i]
                        text = results["documents"][i]
                        metadata = results["metadatas"][i]
                        
                        # Process metadata
                        processed_metadata = metadata.copy()
                        
                        # Convert JSON strings back to objects
                        if "heading_path" in processed_metadata:
                            processed_metadata["heading_path"] = json.loads(processed_metadata["heading_path"])
                        if "bounding_box" in processed_metadata:
                            processed_metadata["bounding_box"] = json.loads(processed_metadata["bounding_box"])
                        
                        # Add chunk
                        chunks.append({
                            "chunk_id": chunk_id,
                            "text": text,
                            "metadata": processed_metadata
                        })
                
                log_step("Storage", f"Found {len(chunks)} chunks for document {document_id}")
                return chunks
                
            except Exception as e:
                log_step("Storage", f"Error getting document chunks: {str(e)}", level="error")
                return []