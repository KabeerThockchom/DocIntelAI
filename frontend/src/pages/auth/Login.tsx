import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Divider,
  Alert,
  CircularProgress,
  Container,
  Grid,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import GoogleIcon from '@mui/icons-material/Google';
import DescriptionIcon from '@mui/icons-material/Description';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import StorageIcon from '@mui/icons-material/Storage';
import { useAuth } from '../../context/AuthContext';
import { useThemeContext } from '../../context/ThemeContext';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { signIn, googleSignIn, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const theme = useTheme();
  const { darkMode } = useThemeContext();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError('Please enter both email and password');
      return;
    }

    try {
      const { error } = await signIn(email, password);
      if (error) {
        setError(error.message);
      } else {
        navigate('/');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
      console.error('Login error:', err);
    }
  };

  const handleGoogleLogin = async () => {
    setError(null);
    try {
      await googleSignIn();
      // Note: The redirect happens automatically so we don't need to navigate
    } catch (err) {
      setError('An error occurred with Google Sign-In. Please try again.');
      console.error('Google login error:', err);
    }
  };

  const FeatureItem = ({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) => (
    <Box sx={{ 
      display: 'flex', 
      alignItems: 'flex-start', 
      mb: isMobile ? 2 : 3,
      '&:last-child': {
        mb: 0
      }
    }}>
      <Box sx={{ 
        mr: isMobile ? 1.5 : 2, 
        bgcolor: 'var(--theme-primary)', 
        color: 'var(--theme-secondary)', 
        p: isMobile ? 0.75 : 1, 
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: darkMode ? '0 0 8px var(--theme-primary-opacity-medium)' : 'none',
        flexShrink: 0
      }}>
        {icon}
      </Box>
      <Box>
        <Typography 
          variant={isMobile ? "subtitle1" : "h6"} 
          gutterBottom 
          sx={{ 
            fontWeight: 'bold', 
            color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
            mb: isMobile ? 0.5 : 1
          }}
        >
          {title}
        </Typography>
        <Typography 
          variant={isMobile ? "body2" : "body1"} 
          color={darkMode ? 'var(--ey-white)' : 'var(--theme-secondary-opacity-medium)'}
          sx={{
            fontSize: isMobile ? '0.875rem' : '1rem'
          }}
        >
          {description}
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ 
      minHeight: '100vh',
      width: '100vw',
      bgcolor: darkMode ? 'var(--theme-secondary)' : 'var(--ey-light-gray)',
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      overflowY: 'auto',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <Container maxWidth="lg" sx={{ 
        height: '100%',
        display: 'flex', 
        alignItems: 'center',
        py: isMobile ? 2 : 4,
        minHeight: isMobile ? 'auto' : '100%'
      }}>
        <Paper
          elevation={darkMode ? 6 : 3}
          sx={{
            width: '100%',
            maxWidth: isMobile ? '100%' : '1200px',
            overflow: 'hidden',
            borderRadius: 2,
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            border: darkMode ? '1px solid var(--theme-primary-opacity-low)' : 'none',
            boxShadow: darkMode ? 
              '0 4px 20px rgba(0, 0, 0, 0.5)' : 
              '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
            height: isMobile ? 'auto' : '600px',
            maxHeight: isMobile ? '90vh' : 'none',
            overflowY: isMobile ? 'auto' : 'hidden'
          }}
        >
          {/* Login Form Section */}
          <Box
            sx={{
              flex: isMobile ? '1' : '0 0 40%',
              p: isMobile ? 2 : 4,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              bgcolor: darkMode ? 'var(--theme-secondary)' : 'var(--ey-white)',
              minHeight: isMobile ? 'auto' : '100%'
            }}
          >
            <Typography 
              component="h1" 
              variant={isMobile ? "h5" : "h4"} 
              sx={{ 
                mb: isMobile ? 2 : 3, 
                fontWeight: 'bold',
                textAlign: isMobile ? 'center' : 'left'
              }}
            >
              Sign In
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 2, width: '100%' }}>
                {error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleEmailLogin} sx={{ width: '100%' }}>
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    '& fieldset': {
                      borderColor: darkMode ? 'var(--theme-primary-opacity-medium)' : 'var(--theme-secondary-opacity-medium)',
                    },
                    '&:hover fieldset': {
                      borderColor: darkMode ? 'var(--theme-primary-opacity-high)' : 'var(--theme-secondary-opacity-medium)',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: 'var(--theme-primary)',
                    },
                  },
                  '& .MuiInputLabel-root': {
                    color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
                  },
                  '& .MuiInputBase-input': {
                    color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
                  }
                }}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type="password"
                id="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    '& fieldset': {
                      borderColor: darkMode ? 'var(--theme-primary-opacity-medium)' : 'var(--theme-secondary-opacity-medium)',
                    },
                    '&:hover fieldset': {
                      borderColor: darkMode ? 'var(--theme-primary-opacity-high)' : 'var(--theme-secondary-opacity-medium)',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: 'var(--theme-primary)',
                    },
                  },
                  '& .MuiInputLabel-root': {
                    color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
                  },
                  '& .MuiInputBase-input': {
                    color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
                  }
                }}
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ 
                  mt: isMobile ? 2 : 3, 
                  mb: isMobile ? 1.5 : 2,
                  bgcolor: 'var(--theme-primary)',
                  color: 'var(--theme-secondary)',
                  '&:hover': {
                    bgcolor: 'var(--theme-primary)',
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s ease-in-out',
                    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)',
                  },
                  transition: 'all 0.2s ease-in-out',
                }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : 'Sign In'}
              </Button>
            </Box>

            <Divider sx={{ 
              my: isMobile ? 1.5 : 2, 
              width: '100%', 
              '&::before, &::after': {
                borderColor: darkMode ? 'var(--theme-secondary-opacity-low)' : 'var(--theme-secondary-opacity-low)',
              },
              color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)'
            }}>or</Divider>

            <Button
              fullWidth
              variant="outlined"
              startIcon={<GoogleIcon />}
              onClick={handleGoogleLogin}
              disabled={loading}
              sx={{ 
                mb: isMobile ? 1.5 : 2,
                borderColor: darkMode ? 'var(--theme-primary-opacity-medium)' : 'var(--theme-primary)',
                color: darkMode ? 'var(--theme-primary)' : 'var(--theme-primary)',
                '&:hover': {
                  borderColor: darkMode ? 'var(--theme-primary)' : 'var(--theme-primary-dark)',
                  bgcolor: darkMode ? 'var(--theme-primary-opacity-low)' : 'var(--theme-primary-opacity-low)',
                  transform: 'translateY(-2px)',
                  transition: 'all 0.2s ease-in-out',
                },
                transition: 'all 0.2s ease-in-out',
              }}
            >
              Sign in with Google
            </Button>

            <Box sx={{ mt: isMobile ? 1.5 : 2, width: '100%', textAlign: 'center' }}>
              <Link to="/forgot-password" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" sx={{ color: 'var(--theme-primary)' }}>
                  Forgot password?
                </Typography>
              </Link>
              <Typography variant="body2" sx={{ mt: isMobile ? 1 : 2, color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)' }}>
                Don't have an account?{' '}
                <Link to="/signup" style={{ textDecoration: 'none', color: 'var(--theme-primary)', fontWeight: 500 }}>
                  Sign Up
                </Link>
              </Typography>
            </Box>
          </Box>

          {/* Welcome Section */}
          <Box
            sx={{
              flex: isMobile ? '1' : '0 0 60%',
              bgcolor: darkMode ? 'var(--theme-secondary)' : 'var(--theme-primary)',
              color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
              p: isMobile ? 2 : 6,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              position: 'relative',
              overflow: 'hidden',
              borderLeft: darkMode ? '1px solid var(--theme-primary-opacity-low)' : 'none',
              borderTop: isMobile ? (darkMode ? '1px solid var(--theme-primary-opacity-low)' : 'none') : 'none',
              minHeight: isMobile ? 'auto' : '100%'
            }}
          >
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                right: 0,
                bottom: 0,
                left: 0,
                background: darkMode 
                  ? 'linear-gradient(45deg, var(--theme-primary-opacity-low) 0%, var(--theme-primary-opacity-low) 100%)'
                  : 'linear-gradient(45deg, var(--theme-secondary-opacity-medium) 0%, var(--theme-secondary-opacity-low) 100%)',
                zIndex: 1,
              }}
            />
            
            <Box sx={{ position: 'relative', zIndex: 2 }}>
              <Typography variant={isMobile ? "h4" : "h3"} fontWeight="bold" gutterBottom>
                Welcome to docintel
              </Typography>
              
              <Typography variant={isMobile ? "subtitle1" : "h6"} gutterBottom sx={{ 
                mb: isMobile ? 3 : 4, 
                opacity: darkMode ? 1 : 0.9,
                color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)'
              }}>
                Your AI-powered document intelligence platform
              </Typography>
              
              <FeatureItem 
                icon={<DescriptionIcon />} 
                title="Document Processing" 
                description="Easily upload, process, and extract insights from your documents, including PDFs, Word documents, and spreadsheets."
              />
              
              <FeatureItem 
                icon={<SmartToyIcon />} 
                title="AI-Powered Analysis" 
                description="Leverage advanced AI models to understand, summarize, and answer questions about your documents."
              />
              
              <FeatureItem 
                icon={<StorageIcon />} 
                title="Organized Knowledge Base" 
                description="Build a searchable knowledge base from your documents for rapid information retrieval."
              />
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default Login; 