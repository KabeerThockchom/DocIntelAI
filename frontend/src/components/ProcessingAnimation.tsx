import React, { useEffect, useState, useRef } from 'react';
import { Box, Typography, LinearProgress, Paper, Fade, keyframes, CircularProgress, Collapse, Chip } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import PsychologyIcon from '@mui/icons-material/Psychology';
import SplitscreenIcon from '@mui/icons-material/Splitscreen';
import FindInPageIcon from '@mui/icons-material/FindInPage';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ArrowRightAltIcon from '@mui/icons-material/ArrowRightAlt';
import { ProcessingStage } from '../services/chatService';

// Define keyframes for animations
const pulse = keyframes`
  0% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.6;
  }
`;

const progress = keyframes`
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
`;

interface ProcessingAnimationProps {
  stage: ProcessingStage;
  message: string;
  subQueries?: string[];
}

const ProcessingAnimation: React.FC<ProcessingAnimationProps> = ({ stage, message, subQueries = [] }) => {
  const [messageHistory, setMessageHistory] = useState<string[]>([]);
  const prevStageRef = useRef<ProcessingStage | null>(null);
  const prevMessageRef = useRef<string | null>(null);
  const [isNewMessage, setIsNewMessage] = useState(false);
  const [visibleQueries, setVisibleQueries] = useState<string[]>([]);
  
  // Keep track of message history and detect new messages
  useEffect(() => {
    if (message) {
      if (!messageHistory.includes(message)) {
        setMessageHistory(prev => [...prev.slice(-1), message]);
      }
      
      if (prevMessageRef.current !== message) {
        setIsNewMessage(true);
        
        // Reset new message flag after animation
        const timer = setTimeout(() => {
          setIsNewMessage(false);
        }, 600);
        
        // Update previous message
        prevMessageRef.current = message;
        
        return () => clearTimeout(timer);
      }
    }
  }, [message, messageHistory]);

  // Detect stage changes
  useEffect(() => {
    // Update previous stage
    prevStageRef.current = stage;
  }, [stage]);

  // Animate the appearance of sub-queries one by one
  useEffect(() => {
    if (subQueries.length === 0) {
      setVisibleQueries([]);
      return;
    }
    
    setVisibleQueries([]);
    
    // Log that we received subQueries
    console.log(`ProcessingAnimation received ${subQueries.length} subQueries:`, subQueries);
    
    // Add each sub-query with a delay
    subQueries.forEach((query, index) => {
      setTimeout(() => {
        console.log(`Adding subQuery to visible list: ${query}`);
        setVisibleQueries(prev => [...prev, query]);
      }, 500 + (index * 300)); // Stagger the appearance
    });
  }, [subQueries]);

  // Define icons for each stage
  const getStageIcon = () => {
    switch (stage) {
      case 'analyzing_query':
        return <SearchIcon />;
      case 'deciding_retrieval':
        return <PsychologyIcon />;
      case 'splitting_query':
        return <SplitscreenIcon />;
      case 'retrieving_documents':
        return <FindInPageIcon />;
      case 'generating_answer':
        return <AutoAwesomeIcon />;
      default:
        return <AutoAwesomeIcon />;
    }
  };

  // Define colors for each stage using theme CSS variables
  const getStageColor = () => {
    switch (stage) {
      case 'analyzing_query':
        return 'var(--theme-primary)'; // Primary theme color for first stage
      case 'deciding_retrieval':
        return 'var(--theme-primary)'; 
      case 'splitting_query':
        return 'var(--theme-primary)';
      case 'retrieving_documents':
        return 'var(--theme-secondary)';
      case 'generating_answer':
        return 'var(--theme-secondary)';
      default:
        return 'var(--theme-secondary)';
    }
  };

  return (
    <Fade in={true} timeout={300}>
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'flex-start',
        maxWidth: '90%',
        alignSelf: 'flex-start',
        mb: 2
      }}>
        <Paper 
          elevation={1} 
          sx={{ 
            p: 1.5, 
            display: 'flex', 
            alignItems: 'center',
            backgroundColor: 'var(--theme-secondary-opacity-high)',
            borderRadius: 2,
            width: '100%',
            border: '1px solid',
            borderColor: 'var(--theme-border)',
            transition: 'all 0.3s ease-in-out',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {/* Animated progress bar */}
          <Box 
            sx={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              right: 0,
              height: '2px',
              bgcolor: getStageColor(),
              overflow: 'hidden',
              '&::after': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'var(--theme-secondary)',
                opacity: 0.3,
                animation: `${progress} 2s infinite ease-in-out`
              }
            }} 
          />
          
          <Box 
            sx={{ 
              display: 'flex', 
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
              mr: 1.5,
              animation: isNewMessage ? `${pulse} 1s` : 'none',
            }}
          >
            <CircularProgress 
              size={30} 
              thickness={4} 
              sx={{ 
                color: getStageColor(),
                position: 'absolute',
                opacity: 0.6
              }}
            />
            <Box 
              sx={{ 
                color: getStageColor(),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1
              }}
            >
              {getStageIcon()}
            </Box>
          </Box>
          
          <Box sx={{ flexGrow: 1 }}>
            <Typography 
              variant="body2" 
              sx={{ 
                fontWeight: 'medium',
                color: 'text.primary',
                transition: 'opacity 0.3s ease-in-out',
                opacity: isNewMessage ? 1 : 0.9
              }}
            >
              {message}
            </Typography>
            
            {messageHistory.length > 1 && (
              <Typography 
                variant="caption" 
                sx={{ 
                  display: 'block',
                  color: 'text.secondary',
                  opacity: 0.7,
                  maxWidth: '100%',
                  textOverflow: 'ellipsis',
                  overflow: 'hidden',
                  whiteSpace: 'nowrap'
                }}
              >
                {messageHistory[0]}
              </Typography>
            )}
          </Box>
        </Paper>

        {/* Display subqueries if we're in the splitting_query stage and have subQueries */}
        {stage === 'splitting_query' && subQueries.length > 0 && (
          <Box sx={{ 
            mt: 1.5, 
            ml: 3, 
            width: '90%',
            display: 'flex',
            flexDirection: 'column',
            gap: 1,
            position: 'relative',
            zIndex: 10
          }}>
            {/* Show how many subqueries we're processing */}
            <Typography 
              variant="caption" 
              color="text.secondary" 
              sx={{ 
                ml: 1, 
                mb: 0.5, 
                fontStyle: 'italic',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <SplitscreenIcon fontSize="small" sx={{ mr: 0.5, color: 'var(--theme-primary)' }} />
              Breaking down into {subQueries.length} searchable parts...
            </Typography>
            
            {visibleQueries.map((query, index) => (
              <Collapse 
                in={true} 
                key={index}
                timeout={500}
              >
                <Paper
                  elevation={1}
                  sx={{
                    p: 1.5,
                    backgroundColor: 'var(--theme-primary-opacity-low)',
                    border: '1px solid var(--theme-primary-opacity-medium)',
                    borderRadius: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    width: '100%',
                    animation: `${pulse} 2s infinite ease-in-out`,
                    animationDelay: `${index * 0.5}s`,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                    '&:hover': {
                      backgroundColor: 'var(--theme-primary-opacity-medium)',
                      transform: 'translateY(-2px)',
                      transition: 'all 0.3s ease'
                    }
                  }}
                >
                  <Chip 
                    label={`Part ${index + 1}`} 
                    size="small" 
                    color="primary"
                    variant="outlined"
                    sx={{ mr: 1 }}
                  />
                  <ArrowRightAltIcon 
                    fontSize="small" 
                    sx={{ mr: 1, color: 'var(--theme-neutral)' }}
                  />
                  <Typography variant="body2" sx={{ fontWeight: 'medium', color: 'var(--theme-text-primary)' }}>
                    {query}
                  </Typography>
                </Paper>
              </Collapse>
            ))}
          </Box>
        )}
      </Box>
    </Fade>
  );
};

export default ProcessingAnimation; 