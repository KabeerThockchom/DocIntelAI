import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useAuth } from './AuthContext';
import supabase, { initializeSchema } from '../services/supabaseClient';

// Define types for our application state
interface AppState {
  lastVisitedDocumentId?: string;
  lastChatSessionId?: string;
  searchHistory?: string[];
  uploadHistory?: {
    lastUploadDate?: string;
    uploadCount?: number;
  };
  preferences?: {
    darkMode?: boolean;
    sidebarCollapsed?: boolean;
    [key: string]: any;
  };
  [key: string]: any;
}

interface StateContextType {
  state: AppState;
  updateState: (newState: Partial<AppState>) => Promise<void>;
  clearState: () => Promise<void>;
}

// Create context
const StateContext = createContext<StateContextType | undefined>(undefined);

// State provider component
export const StateProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [state, setState] = useState<AppState>({});
  const [isLoading, setIsLoading] = useState(true);

  // Initialize Supabase schema on first load
  useEffect(() => {
    initializeSchema().catch(err => {
      console.warn('Schema initialization failed, will try again when needed:', err);
    });
  }, []);

  // Load state from local storage and Supabase on mount or user change
  useEffect(() => {
    const loadState = async () => {
      setIsLoading(true);
      
      // Start with state from localStorage for quick loading
      const localState = localStorage.getItem('appState');
      if (localState) {
        try {
          setState(JSON.parse(localState));
        } catch (error) {
          console.error('Error parsing local state:', error);
        }
      }
      
      // If user is authenticated, try to load state from Supabase
      if (user) {
        try {
          // Query the user's state from Supabase
          const { data, error } = await supabase
            .from('user_states')
            .select('state')
            .eq('user_id', user.id)
            .single();
            
          if (error) {
            console.error('Error loading state from Supabase:', error);
            // Try to initialize the table if it doesn't exist
            if (error.code === '42P01') {
              await initializeSchema();
            }
            // Continue with local state instead of failing
            console.log('Continuing with local state due to Supabase error');
          } else if (data) {
            // Update state with data from Supabase
            setState(currentState => ({
              ...currentState,
              ...data.state
            }));
            
            // Update localStorage with the merged state
            localStorage.setItem('appState', JSON.stringify({
              ...state,
              ...data.state
            }));
          }
        } catch (error) {
          console.error('Error loading state:', error);
          // Continue with local state instead of failing completely
          console.log('Continuing with local state due to error');
        }
      }
      
      setIsLoading(false);
    };
    
    loadState();
  }, [user]);

  // Update state function
  const updateState = async (newState: Partial<AppState>) => {
    // Update local state
    const updatedState = { ...state, ...newState };
    setState(updatedState);
    
    // Update localStorage
    localStorage.setItem('appState', JSON.stringify(updatedState));
    
    // Update Supabase if authenticated
    if (user) {
      try {
        const { error } = await supabase
          .from('user_states')
          .upsert({
            user_id: user.id,
            state: updatedState,
            updated_at: new Date().toISOString()
          });
          
        if (error) {
          console.error('Error saving state to Supabase:', error);
        }
      } catch (error) {
        console.error('Error updating state:', error);
      }
    }
  };

  // Clear state function
  const clearState = async () => {
    // Clear local state
    setState({});
    localStorage.removeItem('appState');
    
    // Clear Supabase state if authenticated
    if (user) {
      try {
        const { error } = await supabase
          .from('user_states')
          .delete()
          .eq('user_id', user.id);
          
        if (error) {
          console.error('Error clearing state from Supabase:', error);
        }
      } catch (error) {
        console.error('Error clearing state:', error);
      }
    }
  };

  // If still loading initial state, you could render a loading indicator
  // or just return the children and let them handle their own loading states
  
  return (
    <StateContext.Provider value={{ state, updateState, clearState }}>
      {children}
    </StateContext.Provider>
  );
};

// Custom hook to use the state context
export const useAppState = (): StateContextType => {
  const context = useContext(StateContext);
  if (context === undefined) {
    throw new Error('useAppState must be used within a StateProvider');
  }
  return context;
};

export default StateContext; 