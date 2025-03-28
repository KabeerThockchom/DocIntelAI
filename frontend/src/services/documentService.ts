import api from './api';
import supabase from './supabaseClient';

// Types
export interface DocumentMetadata {
  title?: string;
  description?: string;
  tags?: string[];
  document_type?: string;
  created_by?: string;
  [key: string]: any;
}

export interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  size?: string;
  createdTime: string;
  modifiedTime: string;
  parents?: string[];
  webViewLink?: string;
  fileType?: string;
}

export interface DriveMetadata {
  created_by?: string;
  user_id?: string;
  tags?: string[];
  additional_metadata?: Record<string, any>;
}

export interface ProcessingResult {
  status: string;
  document_id?: string;
  filename?: string;
  file_type?: string;
  total_chunks?: number;
  error?: string;
}

export interface QueryRequest {
  query: string;
  filter_document_types?: string[];
  filter_tags?: string[];
  filter_date_range?: {
    start_date: string;
    end_date: string;
  };
  top_k?: number;
  include_metadata?: boolean;
  n_results?: number;
  filter_criteria?: {
    source_document_type?: string;
    [key: string]: any;
  };
}

export interface DocumentSummary {
  document_id: string;
  filename: string;
  file_type: string;
  title?: string;
  description?: string;
  tags: string[];
  created_at: string;
  document_type: string;
  status: string;
  [key: string]: any;
}

export interface DocumentDetail {
  document_id: string;
  filename: string;
  file_type: string;
  title?: string;
  description?: string;
  tags: string[];
  created_at: string;
  document_type: string;
  status: string;
  chunks?: Array<{
    chunk_id: string;
    text: string;
    metadata: {
      page_number?: number;
      [key: string]: any;
    };
  }>;
  [key: string]: any;
}

export interface StatisticsResponse {
  total_documents: number;
  documents_by_type?: Record<string, number>;
  document_types?: Record<string, number>;
  total_chunks?: number;
  total_ocr_chunks?: number;
  ocr_percentage?: number;
  avg_chunks_per_document?: number;
  storage_usage?: {
    total_bytes: number;
    by_document_type: Record<string, number>;
  };
  embedding_stats?: {
    total_chunks: number;
    average_chunks_per_document: number;
  };
}

// Drive API functions
export const driveService = {
  // Check if the user has valid Google Drive credentials
  checkDriveCredentials: async () => {
    try {
      // First check if credentials exist in Supabase user metadata
      const { data: userData } = await supabase.auth.getUser();
      const user = userData?.user;
      
      if (user?.user_metadata?.drive_access_token) {
        // If we have a token, check if it's still valid
        const response = await api.get('/drive/validate-token', {
          headers: {
            'X-Drive-Access-Token': user.user_metadata.drive_access_token
          }
        });
        
        return response.data.valid === true;
      }
      
      return false;
    } catch (error) {
      console.error('Error checking Drive credentials:', error);
      return false;
    }
  },
  
  // Get authorization URL
  getAuthUrl: async (redirectUri?: string) => {
    const response = await api.get('/drive/auth-url', {
      params: { redirect_uri: redirectUri || window.location.origin + '/documents' }
    });
    return response.data.auth_url;
  },
  
  // Authenticate with code
  authenticate: async (code: string) => {
    const response = await api.post('/drive/auth', { code });
    
    // Store tokens in user metadata
    if (response.data.access_token) {
      try {
        await supabase.auth.updateUser({
          data: {
            drive_access_token: response.data.access_token,
            drive_refresh_token: response.data.refresh_token,
            drive_token_expiry: new Date().getTime() + (response.data.expires_in * 1000)
          }
        });
      } catch (error) {
        console.error('Error storing Drive tokens:', error);
      }
    }
    
    return response.data;
  },
  
  // Revoke Drive access
  revokeAccess: async () => {
    try {
      // Get current tokens from user metadata
      const { data: userData } = await supabase.auth.getUser();
      const user = userData?.user;
      
      if (user?.user_metadata?.drive_access_token) {
        // Revoke the token server-side
        await api.post('/drive/revoke', {
          token: user.user_metadata.drive_access_token
        });
        
        // Remove tokens from user metadata
        await supabase.auth.updateUser({
          data: {
            drive_access_token: null,
            drive_refresh_token: null,
            drive_token_expiry: null
          }
        });
      }
      
      return { success: true };
    } catch (error) {
      console.error('Error revoking Drive access:', error);
      return { success: false, error };
    }
  },
  
  // List files
  listFiles: async (folderId?: string, fileTypes?: string[]) => {
    const params: Record<string, any> = {};
    
    if (folderId) {
      params.folder_id = folderId;
    }
    
    if (fileTypes && fileTypes.length > 0) {
      params.file_types = fileTypes.join(',');
    }
    
    // Get user's access token
    const { data: userData } = await supabase.auth.getUser();
    const accessToken = userData?.user?.user_metadata?.drive_access_token;
    
    const headers: Record<string, any> = {};
    if (accessToken) {
      headers['X-Drive-Access-Token'] = accessToken;
    }
    
    const response = await api.get('/drive/files', { 
      params,
      headers
    });
    
    return response.data.files as DriveFile[];
  },
  
  // Process a single file
  processFile: async (fileId: string, metadata?: DriveMetadata) => {
    // Get user data to include in metadata
    const { data: userData } = await supabase.auth.getUser();
    const user = userData?.user;
    
    // Add user info to metadata
    const updatedMetadata: DriveMetadata = {
      ...metadata,
      user_id: user?.id,
      created_by: user?.email || metadata?.created_by,
    };
    
    // Get user's access token
    const accessToken = user?.user_metadata?.drive_access_token;
    
    const headers: Record<string, any> = {};
    if (accessToken) {
      headers['X-Drive-Access-Token'] = accessToken;
    }
    
    const response = await api.post('/drive/process-file', {
      file_id: fileId,
      metadata: updatedMetadata
    }, { headers });
    
    return response.data as ProcessingResult;
  },
  
  // Process multiple files
  processFiles: async (fileIds: string[], metadata?: DriveMetadata) => {
    // Get user data to include in metadata
    const { data: userData } = await supabase.auth.getUser();
    const user = userData?.user;
    
    // Add user info to metadata
    const updatedMetadata: DriveMetadata = {
      ...metadata,
      user_id: user?.id,
      created_by: user?.email || metadata?.created_by,
    };
    
    // Get user's access token
    const accessToken = user?.user_metadata?.drive_access_token;
    
    const headers: Record<string, any> = {};
    if (accessToken) {
      headers['X-Drive-Access-Token'] = accessToken;
    }
    
    const response = await api.post('/drive/process-files', {
      file_ids: fileIds,
      metadata: updatedMetadata
    }, { headers });
    
    return response.data.results as ProcessingResult[];
  },
  
  // Batch process files
  batchProcessFiles: async (fileIds: string[], metadata?: DriveMetadata) => {
    // Process files in batches of 5 to avoid overwhelming the server
    const batchSize = 5;
    const results: ProcessingResult[] = [];
    
    for (let i = 0; i < fileIds.length; i += batchSize) {
      const batch = fileIds.slice(i, i + batchSize);
      const batchResults = await driveService.processFiles(batch, metadata);
      results.push(...batchResults);
    }
    
    return results;
  }
};

// Document Service
export const documentService = {
  // Get system statistics
  getSystemStatistics: async (): Promise<StatisticsResponse> => {
    const response = await api.get('/documents/statistics');
    return response.data;
  },
  
  // Upload a document
  uploadDocument: async (file: File, metadata?: any, useParallelProcessing?: boolean, forceOcr?: boolean) => {
    const formData = new FormData();
    formData.append('file', file);
    
    // Get user data to include in metadata
    const { data: userData } = await supabase.auth.getUser();
    const user = userData?.user;
    
    // Merge user data with provided metadata
    const updatedMetadata = {
      ...metadata,
      user_id: user?.id,
      created_by: user?.email || metadata?.created_by,
    };
    
    formData.append('metadata', JSON.stringify(updatedMetadata));
    
    if (useParallelProcessing !== undefined) {
      formData.append('use_parallel_processing', String(useParallelProcessing));
    }
    
    if (forceOcr !== undefined) {
      formData.append('force_ocr', String(forceOcr));
    }
    
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
  
  // Batch upload documents
  batchUploadDocuments: async (files: File[], metadata?: any) => {
    const results = [];
    
    for (const file of files) {
      try {
        const result = await documentService.uploadDocument(file, metadata);
        results.push({
          filename: file.name,
          success: true,
          document_id: result.document_id,
          ...result
        });
      } catch (error) {
        results.push({
          filename: file.name,
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }
    
    return results;
  },
  
  // List documents
  listDocuments: async (documentType?: string, page: number = 1, pageSize: number = 10) => {
    const params: Record<string, any> = {
      page,
      page_size: pageSize
    };
    
    if (documentType && documentType !== 'all') {
      params.document_type = documentType;
    }
    
    const response = await api.get('/documents/list', { params });
    return response.data;
  },
  
  // Get document details
  getDocumentDetails: async (documentId: string, includeChunks: boolean = false) => {
    const params: Record<string, any> = {};
    
    if (includeChunks) {
      params.include_chunks = true;
    }
    
    const response = await api.get(`/documents/${documentId}`, { params });
    return response.data;
  },
  
  // Get document file
  getDocumentFile: async (documentId: string) => {
    const response = await api.get(`/documents/${documentId}/file`, {
      responseType: 'blob'
    });
    return response.data;
  },
  
  // Get document file URL
  getDocumentFileUrl: (documentId: string) => {
    return `${api.defaults.baseURL}/documents/${documentId}/file`;
  },
  
  // Delete document
  deleteDocument: async (documentId: string) => {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  },
  
  // Query documents
  queryDocuments: async (queryRequest: QueryRequest) => {
    const response = await api.post('/documents/query', queryRequest);
    return response.data;
  }
};

export default driveService; 