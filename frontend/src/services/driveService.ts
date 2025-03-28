import api from './api';
import supabase from './supabaseClient';
import { DocumentMetadata } from './documentService';
import axios from 'axios';

// Types
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
      params: { redirect_uri: redirectUri || 'https://docintel.fly.dev/documents' }
    });
    return response.data.auth_url;
  },
  
  // Authenticate with code
  authenticate: async (code: string) => {
    try {
      console.log('Sending auth code to backend...');
      const response = await api.post('/drive/auth', { code });
      console.log('Auth response from backend:', response.data);
      
      // Store tokens in user metadata if they are returned
      if (response.data.access_token) {
        try {
          console.log('Updating user metadata with tokens...');
          await supabase.auth.updateUser({
            data: {
              drive_access_token: response.data.access_token,
              drive_refresh_token: response.data.refresh_token,
              drive_token_expiry: new Date().getTime() + (response.data.expires_in * 1000)
            }
          });
          console.log('User metadata updated successfully');
        } catch (error) {
          console.error('Error storing Drive tokens in user metadata:', error);
        }
      } else {
        console.log('No tokens received from backend, but authentication was successful');
      }
      
      return response.data;
    } catch (error) {
      console.error('Error in drive service authenticate method:', error);
      if (axios.isAxiosError(error) && error.response) {
        console.error('Response status:', error.response.status);
        console.error('Response data:', error.response.data);
      }
      throw error; // Re-throw to allow calling code to handle it
    }
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

export default driveService; 