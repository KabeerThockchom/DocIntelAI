import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { SnackbarProvider } from 'notistack';
import { Box, CircularProgress, Typography } from '@mui/material';

// Custom Theme Provider
import { ThemeProvider } from './context/ThemeContext';

// Auth and State Providers
import { AuthProvider, useAuth } from './context/AuthContext';
import { StateProvider } from './context/StateContext';
import { UploadProvider } from './context/UploadContext';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Services
import { driveService } from './services/driveService';

// Auth Pages
import Login from './pages/auth/Login';
import Signup from './pages/auth/Signup';
import ForgotPassword from './pages/auth/ForgotPassword';

// Layout
import AppLayout from './components/layout/AppLayout';

// Pages
import Dashboard from './pages/Dashboard';
import DocumentList from './pages/documents/DocumentList';
import DocumentUpload from './pages/documents/DocumentUpload';
import DocumentDetail from './pages/documents/DocumentDetail';
import DocumentViewer from './pages/documents/DocumentViewer';
import ChatSessions from './pages/chat/ChatSessions';
import ChatDetail from './pages/chat/ChatDetail';
import Search from './pages/Search';
import Statistics from './pages/Statistics';
import NotFound from './pages/NotFound';
import Home from './pages/auth/Home';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Override stale time for document-related queries
queryClient.setQueryDefaults(['documents'], {
  staleTime: 0, // Always fetch fresh data for documents
});

// Override stale time for statistics
queryClient.setQueryDefaults(['statistics'], {
  staleTime: 0, // Always fetch fresh data for statistics
});

// OAuth Callback handler component
const GoogleDriveCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const urlParams = new URLSearchParams(location.search);
  const code = urlParams.get('code');
  const state = urlParams.get('state');
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const processOAuthCode = async () => {
      if (code && !processing) {
        setProcessing(true);
        try {
          console.log('Processing Google Drive OAuth code:', code.substring(0, 10) + '...');
          console.log('State parameter:', state);
          console.log('Current location:', location.pathname + location.search);
          
          // Directly authenticate with the drive service
          const result = await driveService.authenticate(code);
          console.log('Authentication successful result:', result);
          
          // Invalidate any relevant queries to ensure fresh data
          queryClient.invalidateQueries({ queryKey: ['driveFiles'] });
          queryClient.invalidateQueries({ queryKey: ['documents'] });
          
          // Add a delay to ensure state updates properly
          setTimeout(() => {
            // Redirect to the documents page with the Drive tab selected
            console.log('Redirecting to documents page...');
            navigate('/documents?tab=1');
          }, 1000);
        } catch (error) {
          console.error('Authentication error:', error);
          setError('Failed to authenticate with Google Drive: ' + (error instanceof Error ? error.message : String(error)));
          setTimeout(() => {
            navigate('/documents');
          }, 3000);
        }
      } else if (!code) {
        setError('No authentication code found in the URL. Please try connecting to Google Drive again.');
        console.error('OAuth callback received but no code parameter found in URL:', location.search);
        setTimeout(() => {
          navigate('/documents');
        }, 3000);
      }
    };
    
    processOAuthCode();
  }, [code, state, navigate, processing, queryClient, location]);
  
  // If user is already authenticated, just redirect to documents
  useEffect(() => {
    if (user && !processing && !error) {
      navigate('/documents?tab=1');
    }
  }, [user, navigate, processing, error]);
  
  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column',
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh', 
      p: 3,
      textAlign: 'center'
    }}>
      {error ? (
        <>
          <Typography variant="h6" color="error" gutterBottom>
            {error}
          </Typography>
          <Typography variant="body1">
            Redirecting you back to documents...
          </Typography>
        </>
      ) : (
        <>
          <CircularProgress size={40} sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Completing Google Drive authentication...
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Please wait while we connect your Google Drive account
          </Typography>
        </>
      )}
    </Box>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <CssBaseline />
        <SnackbarProvider 
          maxSnack={3} 
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          autoHideDuration={5000}
        >
          <AuthProvider>
            <StateProvider>
              <UploadProvider>
                <Router>
                  {/* Define the OAuth callback component inside the Router */}
                  {(() => {
                    // This immediately invoked function lets us define a component with hooks
                    const DriveOAuthCallback = () => {
                      const location = window.location;
                      const navigate = useNavigate();
                      const { user, loading } = useAuth();
                      const hasCode = location.search.includes('code=');
                      
                      React.useEffect(() => {
                        // If user is authenticated, stay on the documents page
                        // If not authenticated but has code, we'll let the component handle the OAuth
                        // If not authenticated and no code, redirect to login
                        if (!loading && !user && !hasCode) {
                          navigate('/login');
                        }
                      }, [user, loading, hasCode, navigate]);
                      
                      // Always render DocumentList which will handle the OAuth code if present
                      return <DocumentList />;
                    };
                    
                    return (
                      <Routes>
                        {/* Auth Routes (public) */}
                        <Route path="/login" element={<Login />} />
                        <Route path="/signup" element={<Signup />} />
                        <Route path="/forgot-password" element={<ForgotPassword />} />
                        <Route path="/home" element={<Home />} />
                        
                        {/* Protected Routes */}
                        <Route element={<ProtectedRoute />}>
                          <Route path="/" element={<AppLayout />}>
                            <Route index element={<Dashboard />} />
                            
                            {/* Document Routes */}
                            <Route path="documents">
                              <Route index element={<DocumentList />} />
                              <Route path="upload" element={<DocumentUpload />} />
                              <Route path=":documentId" element={<DocumentDetail />} />
                              <Route path=":documentId/view" element={<DocumentViewer />} />
                            </Route>
                            
                            {/* Chat Routes */}
                            <Route path="chat">
                              <Route index element={<ChatSessions />} />
                              <Route path=":sessionId" element={<ChatDetail />} />
                            </Route>
                            
                            {/* Search Route */}
                            <Route path="search" element={<Search />} />
                            
                            {/* Statistics Route */}
                            <Route path="statistics" element={<Statistics />} />
                          </Route>
                          
                          {/* 404 Route */}
                          <Route path="*" element={<NotFound />} />
                        </Route>
                        
                        {/* Redirect to login for root path if accessed directly */}
                        <Route path="*" element={<Navigate to="/login" />} />
                      </Routes>
                    );
                  })()}
                </Router>
              </UploadProvider>
            </StateProvider>
          </AuthProvider>
        </SnackbarProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
