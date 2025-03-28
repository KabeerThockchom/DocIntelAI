import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Fade, 
  Chip, 
  Divider, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText,
  Grow,
  Collapse,
  LinearProgress,
  Skeleton,
  Tooltip
} from '@mui/material';
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer';
import SubdivideIcon from '@mui/icons-material/CallSplit';
import SearchIcon from '@mui/icons-material/Search';
import ArrowRightAltIcon from '@mui/icons-material/ArrowRightAlt';

interface QuerySplitVisualizerProps {
  originalQuery: string;
  subQueries: string[];
  previousQuery?: string;  // Optional previous query for context
  isFollowUp?: boolean;    // Whether this is a follow-up question
}

const QuerySplitVisualizer: React.FC<QuerySplitVisualizerProps> = ({ 
  originalQuery, 
  subQueries,
  previousQuery,
  isFollowUp = false
}) => {
  const [visibleQueries, setVisibleQueries] = useState<string[]>([]);
  const [loadingQueries, setLoadingQueries] = useState<boolean>(false);
  const [analysisComplete, setAnalysisComplete] = useState<boolean>(false);
  
  // Animate the appearance of sub-queries one by one
  useEffect(() => {
    if (subQueries.length === 0) {
      setVisibleQueries([]);
      setLoadingQueries(true);
      setAnalysisComplete(false);
      return;
    }
    
    // Reset if original query changes
    setVisibleQueries([]);
    setLoadingQueries(true);
    setAnalysisComplete(false);
    
    // Loading animation for 1 second
    setTimeout(() => {
      setLoadingQueries(false);
      
      // Add each sub-query with a delay
      subQueries.forEach((query, index) => {
        setTimeout(() => {
          setVisibleQueries(prev => [...prev, query]);
          
          // Mark analysis as complete after the last query is shown
          if (index === subQueries.length - 1) {
            setTimeout(() => setAnalysisComplete(true), 500);
          }
        }, 800 + (index * 500)); // Start after 800ms, then 500ms between each
      });
    }, 1000);
  }, [subQueries, originalQuery]);
  
  if (!originalQuery) {
    return null;
  }
  
  // Determine if this is a direct query (not split) or a complex query that was split
  const isDirectQuery = subQueries.length === 1 && subQueries[0] === originalQuery;
  
  return (
    <Fade in={true} timeout={500}>
      <Paper 
        elevation={0} 
        sx={{ 
          p: 2.5, 
          mb: 2, 
          borderRadius: 2,
          backgroundColor: 'var(--theme-secondary-opacity-high)',
          border: '1px solid var(--theme-primary-opacity-low)',
          width: '100%',
          boxShadow: '0 4px 12px var(--theme-secondary-opacity-low)'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
          <SubdivideIcon 
            sx={{ 
              mr: 1.5,
              animation: loadingQueries ? 'pulse 1.5s infinite' : 'none',
              color: 'var(--theme-primary)', 
              fontSize: '1.5rem'
            }} 
          />
          <Typography variant="h6" fontWeight="medium" color="var(--theme-text-primary)" sx={{ flexGrow: 1 }}>
            {isFollowUp ? 'Follow-up Question Analysis' : (isDirectQuery ? 'Question Analysis' : 'Query Breakdown')} {loadingQueries && '(Processing...)'}
          </Typography>
          
          {loadingQueries && (
            <LinearProgress 
              sx={{ 
                ml: 2, 
                width: '120px',
                height: 4, 
                borderRadius: 2,
                '& .MuiLinearProgress-bar': {
                  backgroundColor: 'var(--theme-primary)', 
                },
                backgroundColor: 'var(--theme-neutral)', 
              }} 
            />
          )}
          
          {isFollowUp && !loadingQueries && (
            <Chip 
              size="small"
              label="Follow-up" 
              variant="outlined"
              sx={{ 
                ml: 2, 
                animation: 'fadeIn 0.5s ease-in-out',
                borderColor: 'var(--theme-primary)', 
                color: 'var(--theme-text-primary)', 
                backgroundColor: 'var(--theme-primary-opacity-low)',
                fontWeight: 'medium'
              }}
            />
          )}
          
          {analysisComplete && (
            <Chip 
              size="small"
              label="Complete" 
              variant="outlined"
              sx={{ 
                ml: 2, 
                animation: 'fadeIn 0.5s ease-in-out',
                borderColor: 'var(--theme-primary)', 
                color: 'var(--theme-text-primary)', 
                backgroundColor: 'var(--theme-primary-opacity-low)',
                fontWeight: 'medium'
              }}
            />
          )}
        </Box>
        
        <Divider sx={{ mb: 2, backgroundColor: 'var(--theme-border)', opacity: 0.3 }} />
        
        {/* Show previous query context for follow-up questions */}
        {isFollowUp && previousQuery && (
          <Box sx={{ mb: 3, px: 0.5 }}>
            <Typography variant="subtitle2" color="var(--theme-text-secondary)" gutterBottom fontWeight="medium">
              Previous Question Context
            </Typography>
            <Paper 
              elevation={0} 
              sx={{ 
                p: 2, 
                backgroundColor: 'var(--theme-primary-opacity-low)', 
                borderRadius: 1.5,
                border: '1px solid var(--theme-primary-opacity-medium)', 
                overflowWrap: 'break-word',
                wordBreak: 'break-word'
              }}
            >
              <Typography variant="body1" sx={{ color: 'var(--theme-text-primary)' }}>
                {previousQuery}
              </Typography>
            </Paper>
          </Box>
        )}
        
        <Box sx={{ mb: 3, px: 0.5 }}>
          <Typography variant="subtitle2" color="var(--theme-text-secondary)" gutterBottom fontWeight="medium">
            {isFollowUp ? 'Follow-up Question' : 'Original Question'}
          </Typography>
          <Paper 
            elevation={0} 
            sx={{ 
              p: 2, 
              backgroundColor: 'var(--theme-primary-opacity-low)', 
              borderRadius: 1.5,
              border: '1px solid var(--theme-primary-opacity-medium)', 
              overflowWrap: 'break-word',
              wordBreak: 'break-word'
            }}
          >
            <Typography variant="body1" sx={{ color: 'var(--theme-text-primary)' }}>
              {originalQuery}
            </Typography>
          </Paper>
        </Box>
        
        <Box sx={{ mb: 2, px: 0.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="subtitle2" color="var(--theme-text-secondary)" fontWeight="medium">
              Searchable Components
            </Typography>
            <Chip 
              label={`${visibleQueries.length}/${subQueries.length}`} 
              size="small"
              sx={{ 
                bgcolor: 'var(--theme-primary-opacity-low)',
                color: 'var(--theme-text-primary)',
                fontWeight: 'medium',
                height: '24px',
                minWidth: '48px'
              }}
            />
          </Box>
        </Box>
        
        {/* Analyzed Sub-Queries */}
        <Box sx={{ mt: 3 }}>
          <Typography 
            variant="subtitle2" 
            color="var(--theme-text-secondary)" 
            gutterBottom 
            fontWeight="medium"
            sx={{ display: 'flex', alignItems: 'center' }}
          >
            {isDirectQuery ? (
              <React.Fragment>
                <SearchIcon fontSize="small" sx={{ mr: 1, color: 'var(--theme-primary)' }} />
                Direct Search
              </React.Fragment>
            ) : (
              <React.Fragment>
                <SubdivideIcon fontSize="small" sx={{ mr: 1, color: 'var(--theme-primary)' }} />
                Broken Down Into {subQueries.length} Searches
              </React.Fragment>
            )}
          </Typography>
          
          {loadingQueries ? (
            // Loading skeletons while processing
            <Box sx={{ mt: 1 }}>
              {[1, 2, 3].map((_, index) => (
                <Skeleton 
                  key={index}
                  variant="rounded" 
                  height={50} 
                  sx={{ 
                    mb: 1.5, 
                    backgroundColor: 'var(--theme-secondary-opacity-low)',
                    borderRadius: 1,
                  }} 
                />
              ))}
            </Box>
          ) : (
            <List sx={{ p: 0, mt: 1 }} disablePadding>
              {visibleQueries.map((query, index) => (
                <Grow 
                  key={index}
                  in={true}
                  timeout={800}
                  style={{ transformOrigin: '0 0 0', marginBottom: 12 }}
                >
                  <ListItem
                    sx={{ 
                      p: 2, 
                      backgroundColor: 'var(--theme-secondary-opacity-medium)',
                      borderRadius: 1.5,
                      mb: 1.5,
                      border: '1px solid var(--theme-primary-opacity-low)',
                      transition: 'all 0.3s ease',
                      '&:hover': {
                        backgroundColor: 'var(--theme-secondary-opacity-high)',
                        borderColor: 'var(--theme-primary)',
                      }
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: '36px' }}>
                      {visibleQueries.length === 1 ? (
                        <SearchIcon sx={{ color: 'var(--theme-primary)' }} />
                      ) : (
                        <Typography 
                          sx={{ 
                            width: 24, 
                            height: 24, 
                            borderRadius: '50%', 
                            backgroundColor: 'var(--theme-primary-opacity-low)',
                            color: 'var(--theme-primary)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 'bold',
                            fontSize: '0.75rem',
                            border: '1px solid var(--theme-primary-opacity-medium)'
                          }}
                        >
                          {index + 1}
                        </Typography>
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Typography 
                          sx={{ 
                            color: 'var(--theme-text-primary)',
                            fontWeight: visibleQueries.length === 1 ? 'medium' : 'normal',
                          }}
                        >
                          {query}
                        </Typography>
                      }
                    />
                  </ListItem>
                </Grow>
              ))}
            </List>
          )}
        </Box>
        
        {/* Show information about what happens next */}
        {analysisComplete && (
          <Collapse in={analysisComplete} timeout={800}>
            <Divider sx={{ my: 2, backgroundColor: 'var(--theme-border)', opacity: 0.3 }} />
            <Box 
              sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                p: 1.5, 
                backgroundColor: 'var(--theme-primary-opacity-low)',
                borderRadius: 1.5,
                border: '1px solid var(--theme-primary-opacity-medium)',
              }}
            >
              <ArrowRightAltIcon sx={{ mr: 1.5, color: 'var(--theme-primary)' }} />
              <Typography variant="body2" color="var(--theme-text-secondary)">
                {isFollowUp ? 
                  "Using context from previous questions to provide a comprehensive answer." :
                  (isDirectQuery ? 
                    "Searching directly with your original question." : 
                    "Searching for each component to build a comprehensive answer.")}
              </Typography>
            </Box>
          </Collapse>
        )}
        
        <style dangerouslySetInnerHTML={{
          __html: `
            @keyframes pulse {
              0% { opacity: 0.6; }
              50% { opacity: 1; }
              100% { opacity: 0.6; }
            }
            @keyframes fadeIn {
              from { opacity: 0; transform: translateY(5px); }
              to { opacity: 1; transform: translateY(0); }
            }
          `
        }} />
      </Paper>
    </Fade>
  );
};

export default QuerySplitVisualizer; 