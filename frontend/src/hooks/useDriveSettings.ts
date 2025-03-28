import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useAppState } from '../context/StateContext';

export interface DriveSettings {
  currentFolderId?: string;
  folderPath: Array<{ id: string; name: string }>;
  selectedFileTypes: string[];
  sortBy: string;
  sortDirection: 'asc' | 'desc';
}

export function useDriveSettings() {
  const { user } = useAuth();
  const { state, updateState } = useAppState();
  
  // Initialize from stored state or defaults
  const [settings, setSettings] = useState<DriveSettings>({
    currentFolderId: state.drive?.currentFolderId,
    folderPath: state.drive?.folderPath || [],
    selectedFileTypes: state.drive?.selectedFileTypes || [],
    sortBy: state.drive?.sortBy || 'name',
    sortDirection: state.drive?.sortDirection || 'asc',
  });
  
  // Update the settings and persist to state
  const updateSettings = (newSettings: Partial<DriveSettings>) => {
    setSettings(prev => {
      const updated = { ...prev, ...newSettings };
      
      // Persist to app state
      updateState({
        drive: updated
      });
      
      return updated;
    });
  };
  
  // Initial load from app state
  useEffect(() => {
    if (state.drive) {
      setSettings(prev => ({
        ...prev,
        ...state.drive
      }));
    }
  }, [user?.id]); // Only reload when user changes
  
  return {
    settings,
    updateSettings
  };
}

export default useDriveSettings; 