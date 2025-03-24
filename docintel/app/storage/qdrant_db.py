import os
from typing import List, Dict, Any, Optional, Union
import json
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Condition
from app.chunking.models import DocumentChunk, ProcessedDocument
from app.utils.logging import log_step, Timer


class QdrantDBStorage:
    """Storage for document chunks and embeddings using Qdrant."""
    
    def __init__(self, collection_name: str = "documents", user_id: Optional[str] = None):
        """
        Initialize Qdrant storage.
        
        Args:
            collection_name: Base name for the collection
            user_id: Optional user ID for user-specific collections
        """
        self.user_id = user_id
        
        # Form collection name with optional user_id
        self.collection_name = f"{collection_name}_{user_id}" if user_id else collection_name
        
        # Get Qdrant configuration from environment
        qdrant_url = os.environ.get("QDRANT_URL")
        qdrant_api_key = os.environ.get("QDRANT_API_KEY")
        
        if not qdrant_url:
            raise ValueError("QDRANT_URL environment variable is not set")
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key
        )
        
        # Create collection if it doesn't exist
        self._create_collection_if_not_exists()
        
        log_step("Storage", f"Using Qdrant collection: {self.collection_name}")
    
    def _create_collection_if_not_exists(self):
        """Create the collection if it doesn't already exist."""
        try:
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),  # Assuming 1536-dim embeddings (adjust as needed)
                )
                log_step("Storage", f"Created Qdrant collection: {self.collection_name}")
            else:
                log_step("Storage", f"Using existing Qdrant collection: {self.collection_name}")
        except Exception as e:
            log_step("Storage", f"Error creating/checking collection: {str(e)}", level="error")
            raise
    
    def _generate_uuid_from_string(self, input_string: str) -> str:
        """
        Generate a deterministic UUID from a string.
        
        Args:
            input_string: String to convert to UUID
            
        Returns:
            UUID as string
        """
        # Create a namespace UUID (using a fixed UUID)
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # RFC 4122 namespace
        # Generate a UUID based on the namespace and the input string
        return str(uuid.uuid5(namespace, input_string))
    
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
        with Timer("Qdrant DB Storage"):
            log_step("Storage", f"Storing document: {document.filename}")
            
            # Prepare points for storage
            points = []
            
            # Track document-level statistics
            ocr_chunk_count = 0
            
            # Extract file path from the first chunk's metadata if available
            file_path = None
            if document.chunks and hasattr(document.chunks[0], 'metadata'):
                file_path = document.chunks[0].metadata.get('file_path')
            
            # If no file path is found in chunks, check if it's in the document metadata
            if not file_path and hasattr(document, 'metadata') and document.metadata:
                file_path = document.metadata.get('file_path')
            
            for chunk in document.chunks:
                # Skip chunks without embeddings
                if chunk.chunk_id not in embeddings:
                    log_step("Storage", f"Skipping chunk {chunk.chunk_id} - no embedding", level="warning")
                    continue
                
                # Count OCR chunks
                if chunk.is_ocr:
                    ocr_chunk_count += 1
                
                # Prepare metadata (payload in Qdrant terminology)
                payload = {
                    "source_document_id": chunk.source_document_id,
                    "source_document_name": chunk.source_document_name,
                    "source_document_type": chunk.source_document_type,
                    "page_number": chunk.page_number if chunk.page_number is not None else -1,
                    "is_ocr": chunk.is_ocr,
                    "created_at": chunk.created_at.isoformat(),
                    "is_document_metadata": False,  # Explicitly mark as not metadata
                    "text": chunk.text,  # Store the text in the payload
                    "user_id": self.user_id  # Add user_id to every chunk
                }
                
                # Add optional metadata if available
                if chunk.heading_path:
                    payload["heading_path"] = json.dumps(chunk.heading_path)
                if chunk.heading_level is not None:
                    payload["heading_level"] = chunk.heading_level
                if chunk.bounding_box:
                    payload["bounding_box"] = json.dumps(chunk.bounding_box)
                
                # Add any additional metadata from the chunk
                for key, value in chunk.metadata.items():
                    if key not in payload and isinstance(value, (str, int, float, bool)):
                        payload[key] = value
                    elif isinstance(value, list) or isinstance(value, dict):
                        payload[key] = json.dumps(value)
                
                # Always make sure file_path is in the metadata if available
                if file_path:
                    payload["file_path"] = file_path
                
                # Check if chunk_id is already a valid UUID - if not, try to parse it
                try:
                    # Try to parse as UUID to validate
                    uuid.UUID(chunk.chunk_id)
                    point_id = chunk.chunk_id
                except ValueError:
                    # Not a valid UUID, generate a new one
                    point_id = self._generate_uuid_from_string(chunk.chunk_id)
                    # Store the original ID in the payload
                    payload["original_chunk_id"] = chunk.chunk_id
                
                # Create a point
                points.append(PointStruct(
                    id=point_id,
                    vector=embeddings[chunk.chunk_id],
                    payload=payload
                ))
            
            # Store document chunks
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                log_step("Storage", f"Stored {len(points)} chunks for document {document.document_id}")
            
            # Store document-level metadata
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
                "user_id": self.user_id,  # Add user_id to document metadata
                "is_document_metadata": True,
                "text": f"Document metadata for {document.filename}",  # Add text field for consistency
                "metadata_type": "DOC_META"  # Add a field to identify this as metadata
            }
            
            # Add file path to document metadata if available
            if file_path:
                document_metadata["file_path"] = file_path
            
            # Check if file_path exists in any chunk's metadata if not already found
            if not file_path:
                for chunk in document.chunks:
                    if hasattr(chunk, 'metadata') and 'file_path' in chunk.metadata:
                        document_metadata["file_path"] = chunk.metadata['file_path']
                        file_path = chunk.metadata['file_path']
                        break
            
            # Generate a valid UUID for document metadata
            # Use deterministic UUID generation to ensure we can find it again
            metadata_id = self._generate_uuid_from_string(f"DOC_META_{document.document_id}")
            document_metadata["original_id"] = f"DOC_META_{document.document_id}"
            
            # Create a zero vector for metadata (since we won't search for it by similarity)
            zero_vector = [0.0] * 1536  # Adjust size as needed
            
            # Store document metadata
            self.client.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(
                    id=metadata_id,
                    vector=zero_vector,
                    payload=document_metadata
                )]
            )
            
            # Add a direct user to document mapping for easier retrieval
            if self.user_id:
                user_doc_original_id = f"USER_DOC_{self.user_id}_{document.document_id}"
                user_doc_id = self._generate_uuid_from_string(user_doc_original_id)
                
                user_doc_metadata = {
                    "user_id": self.user_id,
                    "document_id": document.document_id,
                    "filename": document.filename,
                    "file_path": file_path if file_path else "",
                    "is_user_document_map": True,
                    "text": f"User {self.user_id} document mapping to {document.document_id}",
                    "original_id": user_doc_original_id,
                    "mapping_type": "USER_DOC"
                }
                
                try:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=[PointStruct(
                            id=user_doc_id,
                            vector=zero_vector,
                            payload=user_doc_metadata
                        )]
                    )
                    log_step("Storage", f"Added user-document mapping for user {self.user_id}, document {document.document_id}")
                except Exception as e:
                    log_step("Storage", f"Error adding user-document mapping: {str(e)}", level="warning")
            
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
        with Timer("Qdrant DB Query"):
            log_step("Query", f"Querying for: {query_text[:50]}...")
            
            # Prepare filter - exclude document metadata
            must_conditions = [
                FieldCondition(
                    key="is_document_metadata",
                    match=MatchValue(value=False)
                )
            ]
            
            # Add additional filter criteria if provided
            if filter_criteria:
                for key, value in filter_criteria.items():
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
            
            # Create the filter
            query_filter = Filter(must=must_conditions)
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=n_results,
                query_filter=query_filter,
                with_payload=True
            )
            
            # Format results
            formatted_results = []
            
            for result in search_results:
                # Get data from result
                point_id = result.id
                score = result.score
                payload = result.payload
                
                # Extract text from payload
                text = payload.get("text", "")
                
                # Process metadata - create a copy to avoid modifying the original
                processed_metadata = payload.copy()
                
                # Remove text from metadata to avoid duplication
                if "text" in processed_metadata:
                    del processed_metadata["text"]
                
                # Convert JSON strings back to objects
                if "heading_path" in processed_metadata:
                    processed_metadata["heading_path"] = json.loads(processed_metadata["heading_path"])
                if "bounding_box" in processed_metadata:
                    processed_metadata["bounding_box"] = json.loads(processed_metadata["bounding_box"])
                
                # Use original chunk ID if available, otherwise use the point ID
                chunk_id = payload.get("original_chunk_id", point_id)
                
                # Add result
                formatted_results.append({
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": processed_metadata,
                    "distance": 1.0 - score  # Convert similarity score to distance
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
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="source_document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            
            # Generate a deterministic ID for the metadata record
            metadata_id = self._generate_uuid_from_string(f"DOC_META_{document_id}")
            
            # Delete the document metadata entry
            try:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=[metadata_id]
                )
            except Exception as e:
                log_step("Storage", f"Error deleting document metadata: {str(e)}", level="warning")
            
            # Delete the user-document mapping if user_id is available
            if self.user_id:
                user_doc_id = self._generate_uuid_from_string(f"USER_DOC_{self.user_id}_{document_id}")
                try:
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=[user_doc_id]
                    )
                    log_step("Storage", f"Deleted user-document mapping for user {self.user_id}, document {document_id}")
                except Exception as e:
                    log_step("Storage", f"Error deleting user-document mapping: {str(e)}", level="warning")
            
            # Also delete any entries with document metadata that match this document ID
            try:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="is_document_metadata",
                                match=MatchValue(value=True)
                            ),
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            except Exception as e:
                log_step("Storage", f"Error deleting document metadata entries: {str(e)}", level="warning")
            
            # Also delete any user-document mappings that might exist for this document
            try:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="is_user_document_map",
                                match=MatchValue(value=True)
                            ),
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            except Exception as e:
                log_step("Storage", f"Error deleting additional user-document mappings: {str(e)}", level="warning")
            
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
                documents = []
                
                # First try to get documents using user-document mappings if we have a user_id
                if self.user_id:
                    # Query user-document mappings first
                    user_filter = Filter(
                        must=[
                            FieldCondition(
                                key="is_user_document_map",
                                match=MatchValue(value=True)
                            ),
                            FieldCondition(
                                key="user_id",
                                match=MatchValue(value=self.user_id)
                            )
                        ]
                    )
                    
                    mapping_results = self.client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=user_filter,
                        limit=1000,  # Reasonable limit for most use cases
                        with_payload=True
                    )
                    
                    if mapping_results[0]:  # Check if points are returned
                        log_step("Storage", f"Found {len(mapping_results[0])} document mappings for user {self.user_id}")
                        
                        # Get document IDs from mappings
                        doc_meta_ids = []
                        doc_ids = []
                        
                        for point in mapping_results[0]:
                            payload = point.payload
                            if "document_id" in payload:
                                doc_id = payload["document_id"]
                                doc_ids.append(doc_id)
                                meta_id = self._generate_uuid_from_string(f"DOC_META_{doc_id}")
                                doc_meta_ids.append(meta_id)
                        
                        if doc_meta_ids:
                            # Get document metadata by IDs
                            doc_results = self.client.retrieve(
                                collection_name=self.collection_name,
                                ids=doc_meta_ids,
                                with_payload=True
                            )
                            
                            # Process document metadata
                            for point in doc_results:
                                payload = point.payload
                                if payload.get("is_document_metadata", False):
                                    # Remove unnecessary fields
                                    if "text" in payload:
                                        del payload["text"]
                                    if "is_document_metadata" in payload:
                                        del payload["is_document_metadata"]
                                    if "metadata_type" in payload:
                                        del payload["metadata_type"]
                                    if "original_id" in payload:
                                        del payload["original_id"]
                                    
                                    documents.append(payload)
                
                # If we didn't find documents via mappings or we don't have a user_id, fall back to the normal method
                if not documents:
                    # Prepare filter for document metadata
                    must_conditions = [
                        FieldCondition(
                            key="is_document_metadata",
                            match=MatchValue(value=True)
                        )
                    ]
                    
                    # Add user_id to filter if available and not in filter_criteria
                    if self.user_id and (not filter_criteria or "user_id" not in filter_criteria):
                        must_conditions.append(
                            FieldCondition(
                                key="user_id",
                                match=MatchValue(value=self.user_id)
                            )
                        )
                    
                    # Add additional filter criteria if provided
                    if filter_criteria:
                        for key, value in filter_criteria.items():
                            must_conditions.append(
                                FieldCondition(
                                    key=key,
                                    match=MatchValue(value=value)
                                )
                            )
                    
                    metadata_filter = Filter(must=must_conditions)
                    
                    # Get document metadata entries
                    results = self.client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=metadata_filter,
                        limit=1000,  # Reasonable limit for most use cases
                        with_payload=True
                    )
                    
                    if results[0]:  # Check if points are returned
                        for point in results[0]:
                            payload = point.payload
                            # Remove unnecessary fields
                            if "text" in payload:
                                del payload["text"]
                            if "is_document_metadata" in payload:
                                del payload["is_document_metadata"]
                            if "metadata_type" in payload:
                                del payload["metadata_type"]
                            if "original_id" in payload:
                                del payload["original_id"]
                            
                            documents.append(payload)
                
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
                # Try to get document via user-document mapping first (fastest and most reliable method)
                if self.user_id:
                    user_doc_id = self._generate_uuid_from_string(f"USER_DOC_{self.user_id}_{document_id}")
                    try:
                        mapping_results = self.client.retrieve(
                            collection_name=self.collection_name,
                            ids=[user_doc_id],
                            with_payload=True
                        )
                        
                        if mapping_results:
                            # We found the mapping, now get the document metadata
                            doc_meta_id = self._generate_uuid_from_string(f"DOC_META_{document_id}")
                            
                            doc_results = self.client.retrieve(
                                collection_name=self.collection_name,
                                ids=[doc_meta_id],
                                with_payload=True
                            )
                            
                            if doc_results:
                                document_metadata = doc_results[0].payload
                                
                                # Remove unnecessary fields
                                if "text" in document_metadata:
                                    del document_metadata["text"]
                                if "is_document_metadata" in document_metadata:
                                    del document_metadata["is_document_metadata"]
                                if "metadata_type" in document_metadata:
                                    del document_metadata["metadata_type"]
                                if "original_id" in document_metadata:
                                    del document_metadata["original_id"]
                                
                                return document_metadata
                    except Exception as mapping_error:
                        log_step("Storage", f"Error getting document via mapping: {str(mapping_error)}", level="warning")
                
                # Try to query using metadata filters
                doc_filter = Filter(
                    must=[
                        FieldCondition(
                            key="is_document_metadata",
                            match=MatchValue(value=True)
                        ),
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
                
                # Add user_id to filter if available
                if self.user_id:
                    doc_filter.must.append(
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=self.user_id)
                        )
                    )
                
                # Query for document metadata entry
                results = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=doc_filter,
                    limit=1,
                    with_payload=True
                )
                
                # Return document metadata if found
                if results[0]:
                    document_metadata = results[0][0].payload
                    
                    # Remove unnecessary fields
                    if "text" in document_metadata:
                        del document_metadata["text"]
                    if "is_document_metadata" in document_metadata:
                        del document_metadata["is_document_metadata"]
                    if "metadata_type" in document_metadata:
                        del document_metadata["metadata_type"]
                    if "original_id" in document_metadata:
                        del document_metadata["original_id"]
                    
                    # Verify file path exists and is valid
                    if "file_path" in document_metadata:
                        file_path = document_metadata["file_path"]
                        if not os.path.exists(file_path):
                            log_step("Storage", f"Warning: File path {file_path} does not exist", level="warning")
                    else:
                        log_step("Storage", f"Warning: No file path found for document {document_id}", level="warning")
                    
                    return document_metadata
                
                # If not found with user_id filter, try without user_id filter
                if self.user_id:
                    log_step("Storage", f"Document not found for user {self.user_id}, trying without user filter")
                    general_filter = Filter(
                        must=[
                            FieldCondition(
                                key="is_document_metadata",
                                match=MatchValue(value=True)
                            ),
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id)
                            )
                        ]
                    )
                    
                    general_results = self.client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=general_filter,
                        limit=1,
                        with_payload=True
                    )
                    
                    if general_results[0]:
                        document_metadata = general_results[0][0].payload
                        
                        # Remove unnecessary fields
                        if "text" in document_metadata:
                            del document_metadata["text"]
                        if "is_document_metadata" in document_metadata:
                            del document_metadata["is_document_metadata"]
                        if "metadata_type" in document_metadata:
                            del document_metadata["metadata_type"]
                        if "original_id" in document_metadata:
                            del document_metadata["original_id"]
                        
                        log_step("Storage", f"Found document {document_id} in general collection")
                        return document_metadata
                
                # As a last resort, try getting by DOC_META ID directly
                doc_meta_id = self._generate_uuid_from_string(f"DOC_META_{document_id}")
                try:
                    results = self.client.retrieve(
                        collection_name=self.collection_name,
                        ids=[doc_meta_id],
                        with_payload=True
                    )
                    
                    if results:
                        document_metadata = results[0].payload
                        
                        # Remove unnecessary fields
                        if "text" in document_metadata:
                            del document_metadata["text"]
                        if "is_document_metadata" in document_metadata:
                            del document_metadata["is_document_metadata"]
                        if "metadata_type" in document_metadata:
                            del document_metadata["metadata_type"]
                        if "original_id" in document_metadata:
                            del document_metadata["original_id"]
                        
                        log_step("Storage", f"Found document {document_id} by direct ID lookup")
                        return document_metadata
                except Exception as direct_error:
                    log_step("Storage", f"Error in direct ID lookup: {str(direct_error)}", level="warning")
                
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
                # Create filter for document chunks
                chunk_filter = Filter(
                    must=[
                        FieldCondition(
                            key="source_document_id",
                            match=MatchValue(value=document_id)
                        ),
                        FieldCondition(
                            key="is_document_metadata",
                            match=MatchValue(value=False)
                        )
                    ]
                )
                
                # Get all chunks for this document
                results = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=chunk_filter,
                    limit=1000,  # Reasonable limit for most use cases
                    with_payload=True
                )
                
                # Format results
                chunks = []
                
                if results[0]:
                    for point in results[0]:
                        point_id = point.id
                        payload = point.payload
                        
                        # Extract text from payload
                        text = payload.get("text", "")
                        
                        # Process metadata - create a copy to avoid modifying the original
                        processed_metadata = payload.copy()
                        
                        # Remove text from metadata to avoid duplication
                        if "text" in processed_metadata:
                            del processed_metadata["text"]
                        
                        # Convert JSON strings back to objects
                        if "heading_path" in processed_metadata:
                            processed_metadata["heading_path"] = json.loads(processed_metadata["heading_path"])
                        if "bounding_box" in processed_metadata:
                            processed_metadata["bounding_box"] = json.loads(processed_metadata["bounding_box"])
                        
                        # Use original chunk ID if available, otherwise use the point ID
                        chunk_id = payload.get("original_chunk_id", point_id)
                        
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