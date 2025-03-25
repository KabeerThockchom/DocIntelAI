import os
import io
import json
import tempfile
from typing import List, Dict, Any, Optional, BinaryIO, Union
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from app.utils.logging import log_step, Timer
from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DocxParser
from app.parsers.pptx_parser import PPTXParser
from app.parsers.excel_parser import ExcelParser
from app.chunking.chunker import DocumentChunker
from app.embeddings.embedder import AzureOpenAIEmbedder
from app.storage.qdrant_db import QdrantDBStorage


# Define OAuth 2.0 scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',  # Create/modify files opened with app
    'https://www.googleapis.com/auth/drive.readonly',  # Allow app to appear in "Open with" menu
    'https://www.googleapis.com/auth/drive.install',  # Added to handle drive.install scope
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

# Map of supported file types to their MIME types
MIME_TYPE_MAP = {
    'pdf': ['application/pdf'],
    'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'doc': ['application/msword'],
    'pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
    'ppt': ['application/vnd.ms-powerpoint'],
    'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    'xls': ['application/vnd.ms-excel'],
    'csv': ['text/csv'],
    'txt': ['text/plain'],
    'gdoc': ['application/vnd.google-apps.document'],
    'gsheet': ['application/vnd.google-apps.spreadsheet'],
    'gslides': ['application/vnd.google-apps.presentation']
}

# Initialize components
chunker = DocumentChunker()
embedder = AzureOpenAIEmbedder()
qdrant_db = QdrantDBStorage()

class GoogleDriveClient:
    """Client for interacting with Google Drive API."""
    
    def __init__(self):
        """Initialize Google Drive client with proper paths."""
        # Get the current directory (app/drive)
        current_dir = Path(__file__).parent
        
        # Create paths for credentials and token
        self.credentials_path = current_dir / "credentials.json"
        self.token_path = current_dir / "token.json"
        
        # Log the paths for debugging
        log_step("Google Drive", f"Looking for credentials at: {self.credentials_path}")
        log_step("Google Drive", f"Token will be stored at: {self.token_path}")
        
        self.creds = None
        self.service = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not self.credentials_path.exists():
            log_step("Google Drive", f"Credentials file not found at {self.credentials_path}", level="error")
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
            
        if self.token_path.exists():
            with open(self.token_path, 'r') as token_file:
                token_data = json.load(token_file)
                self.creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            
        # If credentials are invalid or don't exist, run the OAuth flow
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), 
                    SCOPES
                )
                self.creds = flow.run_local_server(port=0)
                
            # Save the credentials for future use
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
        
        # Build the Drive API service
        self.service = build('drive', 'v3', credentials=self.creds)
        
        return True
    
    def list_files(
        self, 
        folder_id: Optional[str] = None,
        file_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List files in Google Drive.
        
        Args:
            folder_id: Folder ID to list files from (root folder if None)
            file_types: List of file extensions to filter by
            
        Returns:
            List of file metadata
        """
        if not self.service:
            if not self.authenticate():
                log_step("Google Drive", "Authentication failed", level="error")
                return []
        
        try:
            # Build query
            query_parts = []
            
            # Add folder filter if provided
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            # Add file type filter if provided
            if file_types:
                mime_types = []
                for ext in file_types:
                    ext = ext.lower().lstrip('.')
                    if ext in MIME_TYPE_MAP:
                        mime_types.extend(MIME_TYPE_MAP[ext])
                
                if mime_types:
                    mime_query = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
                    query_parts.append(f"({mime_query})")
            
            # Combine query parts
            query = " and ".join(query_parts) if query_parts else ""
            
            # List files with pagination
            files = []
            page_token = None
            
            while True:
                # Prepare the list request
                request = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink)",
                    pageToken=page_token,
                    pageSize=1000,  # Maximum allowed page size
                    orderBy="folder,name"  # Sort folders first, then by name
                )
                
                # Execute the request
                response = request.execute()
                
                # Add files to our list
                files.extend(response.get('files', []))
                
                # Update the page token
                page_token = response.get('nextPageToken')
                
                # Break if no more pages
                if not page_token:
                    break
            
            # Post-process the files
            processed_files = []
            for file in files:
                # Convert timestamps to ISO format
                file['createdTime'] = file.get('createdTime', '')
                file['modifiedTime'] = file.get('modifiedTime', '')
                
                # Add file type information
                mime_type = file.get('mimeType', '')
                file['fileType'] = next(
                    (ext for ext, mimes in MIME_TYPE_MAP.items() if mime_type in mimes),
                    'other'
                )
                
                # Add file to processed list
                processed_files.append(file)
            
            return processed_files
            
        except HttpError as e:
            log_step("Google Drive", f"Error listing files: {str(e)}", level="error")
            return []
    
    def download_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Dictionary with file metadata and content, or None if download failed
        """
        if not self.service:
            if not self.authenticate():
                log_step("Google Drive", "Authentication failed", level="error")
                return None
        
        try:
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime"
            ).execute()
            
            # Get file content
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                log_step("Google Drive", f"Download progress: {int(status.progress() * 100)}%")
            
            # Reset file content position
            file_content.seek(0)
            
            return {
                "metadata": file_metadata,
                "content": file_content
            }
            
        except HttpError as e:
            log_step("Google Drive", f"Error downloading file: {str(e)}", level="error")
            return None
    
    def get_auth_url(self) -> str:
        """
        Get OAuth 2.0 authorization URL.
        
        Returns:
            Authorization URL
        """
        if not self.credentials_path.exists():
            log_step("Google Drive", f"Credentials file not found at {self.credentials_path}", level="error")
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
            
        # Create the flow with all required scopes
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.credentials_path), 
            SCOPES,
            # Use proper redirect URI for web application
            redirect_uri="https://docintel.fly.dev/documents"
        )
        
        # Configure authorization parameters
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',  # Always show consent screen to get refresh token
        )
        
        log_step("Google Drive", f"Generated auth URL: {auth_url[:100]}...")
        return auth_url
    
    def exchange_code(self, code: str) -> bool:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code
            
        Returns:
            True if successful, False otherwise
        """
        try:
            log_step("Google Drive", f"Exchanging auth code for token...")
            
            # Create the flow with matching parameters
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path), 
                SCOPES,
                redirect_uri="https://docintel.fly.dev/documents"
            )
            
            # Fetch the token
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            
            # Save the credentials for future use
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
            
            # Build the Drive API service
            self.service = build('drive', 'v3', credentials=self.creds)
            
            log_step("Google Drive", "Authentication successful")
            return True
            
        except Exception as e:
            log_step("Google Drive", f"Error exchanging code: {str(e)}", level="error")
            return False
    
    def process_file(
        self,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            metadata: Additional metadata
            
        Returns:
            Dictionary with processing status and document ID
        """
        try:
            # Download file from Drive
            file_data = self.download_file(file_id)
            if not file_data:
                raise ValueError(f"Failed to download file {file_id}")
            
            file_metadata = file_data["metadata"]
            file_content = file_data["content"]
            filename = file_metadata["name"]
            
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as temp_file:
                temp_file.write(file_content.read())
                temp_path = temp_file.name
            
            try:
                # Process document based on file type
                if file_ext == "pdf":
                    parser = PDFParser(chunker)
                    processed_doc = parser.parse(temp_path, filename, metadata)
                elif file_ext == "docx":
                    parser = DocxParser(chunker)
                    processed_doc = parser.parse(temp_path, filename, metadata)
                elif file_ext == "pptx":
                    parser = PPTXParser(chunker)
                    processed_doc = parser.parse(temp_path, filename, metadata)
                elif file_ext in ["xlsx", "xls", "csv"]:
                    parser = ExcelParser(chunker)
                    processed_doc = parser.parse(temp_path, filename, metadata)
                else:
                    raise ValueError(f"Unsupported file type: {file_ext}")
                
                # Generate embeddings for chunks
                embeddings = embedder.generate_embeddings(processed_doc.chunks)
                
                # Store document and embeddings
                document_id = qdrant_db.store_document(processed_doc, embeddings)
                
                return {
                    "status": "success",
                    "document_id": document_id,
                    "filename": filename,
                    "file_type": file_ext,
                    "total_chunks": len(processed_doc.chunks)
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            log_step("Drive File Processing", f"Error processing file {file_id}: {str(e)}", level="error")
            raise
    
    def process_files(
        self,
        file_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple files from Google Drive.
        
        Args:
            file_ids: List of Google Drive file IDs
            metadata: Additional metadata
            
        Returns:
            List of processing results
        """
        results = []
        
        for file_id in file_ids:
            try:
                result = self.process_file(file_id, metadata)
                results.append(result)
            except Exception as e:
                log_step("Drive Files Processing", f"Error processing file {file_id}: {str(e)}", level="error")
                results.append({
                    "status": "error",
                    "file_id": file_id,
                    "error": str(e)
                })
        
        return results