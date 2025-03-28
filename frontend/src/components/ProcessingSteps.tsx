import React from 'react';
import { 
  Box, 
  Typography, 
  Stepper, 
  Step, 
  StepLabel, 
  Paper, 
  Fade,
  StepIconProps,
  LinearProgress
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import SplitscreenIcon from '@mui/icons-material/Splitscreen';
import FindInPageIcon from '@mui/icons-material/FindInPage';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { ProcessingStage } from '../services/chatService';

interface ProcessingStepsProps {
  stage: ProcessingStage;
  message: string;
  details?: Record<string, any>;
}

// Custom step icon component that changes color based on active state
const CustomStepIcon = (props: StepIconProps & { icon: React.ReactNode, active: boolean }) => {
  const { active, completed, icon } = props;
  
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 40,
        height: 40,
        borderRadius: '50%',
        backgroundColor: completed ? 'var(--theme-primary-opacity-low)' : 
                        active ? 'var(--theme-primary-opacity-low)' : 
                        'transparent',
        border: `2px solid ${completed ? 'var(--theme-primary)' : active ? 'var(--theme-primary)' : 'var(--ey-light-gray)'}`,
        color: completed ? 'var(--theme-primary)' : active ? 'var(--theme-primary)' : 'var(--ey-medium-gray)',
        transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
        boxShadow: completed || active ? '0 2px 8px var(--theme-primary-opacity-medium)' : 'none',
      }}
    >
      {completed ? <CheckCircleOutlineIcon /> : icon}
    </Box>
  );
};

const STEPS = [
  {
    label: 'Analyzing Query',
    stage: 'analyzing_query',
    icon: <SearchIcon />,
    description: 'Understanding your question'
  },
  {
    label: 'Planning Strategy',
    stage: 'deciding_retrieval',
    icon: <HelpOutlineIcon />,
    description: 'Determining search approach'
  },
  {
    label: 'Breaking Down Question',
    stage: 'splitting_query',
    icon: <SplitscreenIcon />,
    description: 'Dividing complex questions'
  },
  {
    label: 'Searching Documents',
    stage: 'retrieving_documents',
    icon: <FindInPageIcon />,
    description: 'Finding relevant information'
  },
  {
    label: 'Generating Answer',
    stage: 'generating_answer',
    icon: <AutoAwesomeIcon />,
    description: 'Creating your response'
  }
];

const ProcessingSteps: React.FC<ProcessingStepsProps> = ({ stage, message, details }) => {
  // Ensure query splitting is shown by always setting retrievalNeeded to true
  const retrievalNeeded = true; // Always include query splitting step
  
  // Filter steps based on retrieval decision
  const filteredSteps = STEPS.filter(step => {
    // Include all steps now that we've set retrievalNeeded to true
    return true;
  });
  
  // Find the index of the current stage in the filtered steps
  const activeStepIndex = filteredSteps.findIndex(step => {
    // Treat 'complete' as if it's still at the last step
    if (stage === 'complete' && step.stage === 'generating_answer') {
      return true;
    }
    return step.stage === stage;
  });
  
  // Check if we're in an error state
  const isError = details?.error === true;
  const hasErrorMessage = message && message.toLowerCase().includes('error');
  
  // Calculate progress percentage (use details.progressPercentage if available)
  const progressPercentage = details?.progressPercentage ? details.progressPercentage :
    Math.round(((activeStepIndex + 1) / filteredSteps.length) * 100);
  
  return (
    <Fade in={true} timeout={500}>
      <Paper 
        elevation={0} 
        sx={{ 
          p: 3, 
          borderRadius: 2, 
          maxWidth: '800px',
          backgroundColor: isError ? 'var(--theme-secondary-opacity-low)' : 'var(--ey-white)',
          border: isError ? '1px solid var(--ey-medium-gray)' : '1px solid var(--ey-light-gray)',
          position: 'relative',
          overflow: 'hidden',
          boxShadow: '0 4px 20px var(--theme-secondary-opacity-low)',
        }}
      >
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          mb: 3
        }}>
          <Typography 
            variant="h6" 
            sx={{ 
              color: isError ? 'error.main' : 'var(--theme-secondary)',
              fontWeight: 'medium',
            }}
          >
            {hasErrorMessage ? 'Error Processing Request' : 'Processing Your Question'}
          </Typography>
          
          {!isError && stage !== 'complete' && (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography 
                variant="caption" 
                sx={{ 
                  mr: 1, 
                  color: 'var(--theme-secondary)',
                  fontWeight: 'medium',
                }}
              >
                {progressPercentage}%
              </Typography>
              <Box sx={{ width: 60 }}>
                <LinearProgress 
                  variant="determinate" 
                  value={progressPercentage} 
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: 'var(--theme-secondary-opacity-low)',
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: 'var(--theme-primary)',
                      borderRadius: 3,
                    }
                  }}
                />
              </Box>
            </Box>
          )}
        </Box>
        
        <Box sx={{ mb: 4 }}>
          <Box
            sx={{ 
              p: 2, 
              borderRadius: 1.5,
              backgroundColor: isError ? 'var(--theme-secondary-opacity-low)' : 'var(--theme-primary-opacity-low)', 
              border: `1px solid ${isError ? 'var(--theme-secondary-opacity-medium)' : 'var(--theme-primary-opacity-medium)'}`,
              boxShadow: '0 2px 8px var(--theme-secondary-opacity-low)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <Typography 
              variant="body1" 
              sx={{ 
                color: isError ? 'var(--ey-medium-gray)' : 'var(--theme-text-primary)', 
                fontWeight: 'medium',
              }}
            >
              {message}
            </Typography>
            
            {!isError && stage !== 'complete' && (
              <Box 
                sx={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  height: 2,
                  width: '30%',
                  backgroundColor: 'var(--theme-primary)',
                  animation: 'progressSlide 2s infinite ease-in-out',
                  borderRadius: 1,
                  opacity: 0.7,
                }}
              />
            )}
          </Box>
          
          {stage === 'splitting_query' && details?.subQueries && (
            <Typography 
              variant="caption" 
              sx={{ 
                display: 'block', 
                mt: 1.5,
                color: 'var(--theme-text-secondary)',
                fontStyle: 'italic',
              }}
            >
              Breaking down into {details.subQueries.length} sub-questions for comprehensive search results.
            </Typography>
          )}
          
          {stage === 'retrieving_documents' && details?.count && (
            <Typography 
              variant="caption" 
              sx={{ 
                display: 'block', 
                mt: 1.5,
                color: 'var(--theme-text-secondary)',
                fontStyle: 'italic',
              }}
            >
              Found {details.count} relevant document chunks to analyze.
            </Typography>
          )}
        </Box>
        
        <Box sx={{ mb: 3 }}>
          <Stepper 
            activeStep={isError ? -1 : activeStepIndex} 
            alternativeLabel
            sx={{ 
              '& .MuiStepConnector-line': {
                minHeight: 3,
                borderTopWidth: 3,
                borderRadius: 5,
                borderColor: '#cccccc',
              },
              '& .MuiStepConnector-active .MuiStepConnector-line': {
                borderColor: '#ffe600',
              },
              '& .MuiStepConnector-completed .MuiStepConnector-line': {
                borderColor: '#ffe600',
              },
            }}
          >
            {filteredSteps.map((step, index) => {
              const isActive = !isError && index === activeStepIndex;
              const isCompleted = !isError && index < activeStepIndex;
              
              return (
                <Step key={step.stage} completed={isCompleted}>
                  <StepLabel 
                    StepIconComponent={(props) => (
                      <CustomStepIcon 
                        {...props} 
                        icon={step.icon} 
                        active={isActive} 
                      />
                    )}
                  >
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        color: isActive ? '#333333' : isCompleted ? '#333333' : '#999999',
                        fontWeight: isActive ? 'bold' : 'normal',
                        transition: 'all 0.5s ease-in-out',
                        display: 'block',
                        textAlign: 'center',
                      }}
                    >
                      {step.label}
                    </Typography>
                    
                    {isActive && (
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          color: '#999999',
                          display: 'block',
                          fontSize: '0.7rem',
                          maxWidth: '120px',
                          textAlign: 'center',
                          mt: 0.5,
                          opacity: 0.8,
                          animation: 'fadeIn 0.5s ease-in-out',
                        }}
                      >
                        {step.description}
                      </Typography>
                    )}
                  </StepLabel>
                </Step>
              );
            })}
          </Stepper>
        </Box>
        
        <Box sx={{ mt: 3, textAlign: 'center' }}>
          <Typography 
            variant="caption" 
            color={isError ? 'var(--theme-text-secondary)' : 'var(--theme-text-secondary)'}
            sx={{ fontStyle: 'italic' }}
          >
            {isError 
              ? "I'm continuing to work on your question in the background." 
              : "Processing complex questions may take a moment to ensure the best results."}
          </Typography>
        </Box>
        
        <style dangerouslySetInnerHTML={{
          __html: `
            @keyframes pulse {
              0% { opacity: 0.6; }
              50% { opacity: 1; }
              100% { opacity: 0.6; }
            }
            
            @keyframes progressAnimation {
              0% { transform: translateX(-100%); }
              50% { transform: translateX(0); }
              100% { transform: translateX(100%); }
            }
            
            @keyframes fadeIn {
              from { opacity: 0; }
              to { opacity: 1; }
            }
            
            @keyframes slideIn {
              from { opacity: 0; transform: translateX(-15px); }
              to { opacity: 1; transform: translateX(0); }
            }
          `
        }} />
      </Paper>
    </Fade>
  );
};

export default ProcessingSteps; 