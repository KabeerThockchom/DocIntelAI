import React, { createContext, useContext, useState, useReducer, ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { useAppState } from './StateContext';

// Define types for our uploads
export interface UploadItem {
  id: string;
  filename: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  error?: string;
  documentId?: string;
  createdAt: Date;
  fileType?: string;
  userId?: string;
}

// Upload context state
interface UploadState {
  uploads: UploadItem[];
  hasActiveUploads: boolean;
}

// Upload actions
type UploadAction = 
  | { type: 'ADD_UPLOAD'; payload: UploadItem }
  | { type: 'UPDATE_UPLOAD'; payload: { id: string; update: Partial<UploadItem> } }
  | { type: 'REMOVE_UPLOAD'; payload: string }
  | { type: 'CLEAR_UPLOADS' };

// Initial state
const initialState: UploadState = {
  uploads: [],
  hasActiveUploads: false
};

// Reducer function
function uploadReducer(state: UploadState, action: UploadAction): UploadState {
  switch (action.type) {
    case 'ADD_UPLOAD':
      return {
        ...state,
        uploads: [...state.uploads, action.payload],
        hasActiveUploads: true
      };
    
    case 'UPDATE_UPLOAD':
      return {
        ...state,
        uploads: state.uploads.map(upload => 
          upload.id === action.payload.id
            ? { ...upload, ...action.payload.update }
            : upload
        ),
        hasActiveUploads: state.uploads.some(upload => 
          upload.id === action.payload.id
            ? action.payload.update.status !== 'completed' && action.payload.update.status !== 'error'
            : upload.status === 'pending' || upload.status === 'uploading' || upload.status === 'processing'
        )
      };
    
    case 'REMOVE_UPLOAD':
      return {
        ...state,
        uploads: state.uploads.filter(upload => upload.id !== action.payload),
        hasActiveUploads: state.uploads
          .filter(upload => upload.id !== action.payload)
          .some(upload => upload.status === 'pending' || upload.status === 'uploading' || upload.status === 'processing')
      };
    
    case 'CLEAR_UPLOADS':
      return {
        ...state,
        uploads: state.uploads.filter(upload => 
          upload.status === 'pending' || upload.status === 'uploading' || upload.status === 'processing'
        ),
        hasActiveUploads: state.uploads.some(upload => 
          upload.status === 'pending' || upload.status === 'uploading' || upload.status === 'processing'
        )
      };
    
    default:
      return state;
  }
}

// Context type
interface UploadContextType {
  state: UploadState;
  addUpload: (upload: Omit<UploadItem, 'id' | 'createdAt' | 'userId'>) => string;
  updateUpload: (id: string, update: Partial<UploadItem>) => void;
  removeUpload: (id: string) => void;
  clearCompleted: () => void;
}

// Create the context
const UploadContext = createContext<UploadContextType | undefined>(undefined);

// Provider component
export const UploadProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const { updateState } = useAppState();
  const [state, dispatch] = useReducer(uploadReducer, initialState);

  // Generate a unique ID for each upload
  const generateId = (): string => {
    return Date.now().toString(36) + Math.random().toString(36).substring(2);
  };

  // Add a new upload
  const addUpload = (upload: Omit<UploadItem, 'id' | 'createdAt' | 'userId'>): string => {
    const id = generateId();
    const newUpload: UploadItem = {
      ...upload,
      id,
      createdAt: new Date(),
      userId: user?.id,
    };

    dispatch({ type: 'ADD_UPLOAD', payload: newUpload });
    
    // Update upload history in app state
    updateState({
      uploadHistory: {
        lastUploadDate: new Date().toISOString(),
        uploadCount: (state.uploads.length + 1)
      }
    });
    
    return id;
  };

  // Update an existing upload
  const updateUpload = (id: string, update: Partial<UploadItem>) => {
    dispatch({ type: 'UPDATE_UPLOAD', payload: { id, update } });
    
    // If the upload is completed, update the document history in app state
    if (update.status === 'completed' && update.documentId) {
      updateState({
        lastUploadedDocumentId: update.documentId,
      });
    }
  };

  // Remove an upload
  const removeUpload = (id: string) => {
    dispatch({ type: 'REMOVE_UPLOAD', payload: id });
  };

  // Clear all completed uploads
  const clearCompleted = () => {
    dispatch({ type: 'CLEAR_UPLOADS' });
  };

  // The context value
  const value: UploadContextType = {
    state,
    addUpload,
    updateUpload,
    removeUpload,
    clearCompleted
  };

  return (
    <UploadContext.Provider value={value}>
      {children}
    </UploadContext.Provider>
  );
};

// Custom hook to use the upload context
export const useUpload = (): UploadContextType => {
  const context = useContext(UploadContext);
  if (context === undefined) {
    throw new Error('useUpload must be used within an UploadProvider');
  }
  return context;
};

export default UploadContext; 