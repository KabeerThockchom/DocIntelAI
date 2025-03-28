import React, { useEffect, useState } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Fade, 
  CircularProgress, 
  Collapse, 
  Chip,
  Divider,
  LinearProgress
} from '@mui/material';
import { CheckCircle, RadioButtonUnchecked } from '@mui/icons-material';
import SearchIcon from '@mui/icons-material/Search';
import SplitscreenIcon from '@mui/icons-material/Splitscreen';
import ArrowRightAltIcon from '@mui/icons-material/ArrowRightAlt';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import FindInPageIcon from '@mui/icons-material/FindInPage';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { ProcessingStage, ProcessingUpdate } from '../services/chatService';
import StepProgressTracker from './StepProgressTracker';

interface Step {
  stage: ProcessingStage;
  title: string;
  description: string;
}

interface ChecklistLoadingProps {
  currentStage: ProcessingStage;
  completedStages: ProcessingStage[];
  message?: string;
  subQueries?: string[];
  processingUpdate?: ProcessingUpdate;
}

const ChecklistLoading: React.FC<ChecklistLoadingProps> = ({ 
  currentStage, 
  completedStages, 
  message, 
  subQueries,
  processingUpdate 
}) => {
  const steps: Step[] = [
    { 
      stage: 'analyzing_query', 
      title: 'Analyzing query', 
      description: 'Understanding your question and identifying key elements.' 
    },
    { 
      stage: 'splitting_query', 
      title: 'Breaking down query', 
      description: 'Dividing complex questions into manageable parts.' 
    },
    { 
      stage: 'retrieving_documents', 
      title: 'Retrieving documents', 
      description: 'Finding relevant documents from the knowledge base.' 
    },
    { 
      stage: 'generating_answer', 
      title: 'Generating answer', 
      description: 'Creating a comprehensive response based on retrieved information.' 
    }
  ];

  // Get current stage index
  const getCurrentStageIndex = () => {
    return steps.findIndex(step => step.stage === currentStage);
  };

  // Check if a step is completed
  const isStepCompleted = (stage: ProcessingStage) => {
    return completedStages.includes(stage);
  };

  // Get appropriate icon for a step
  const getStepIcon = (step: Step, index: number) => {
    const currentIndex = getCurrentStageIndex();
    
    // Step is completed - show checkmark
    if (isStepCompleted(step.stage)) {
      return (
        <Box className="step-icon completed">
          <CheckCircle sx={{ color: 'var(--theme-primary)' }} />
        </Box>
      );
    }
    
    // Current step - show spinner
    if (index === currentIndex) {
      return (
        <Box className="step-icon current">
          <CircularProgress size={24} sx={{ 
            color: 'var(--theme-primary)',
            '.MuiCircularProgress-circle': {
              strokeWidth: 3
            }
          }} />
        </Box>
      );
    }
    
    // Future step - show empty circle
    return (
      <Box className="step-icon pending">
        <RadioButtonUnchecked sx={{ color: '#777' }} />
      </Box>
    );
  };

  // Render sub-queries if available with logging
  const renderSubQueries = () => {
    console.log('ChecklistLoading - renderSubQueries called with:', subQueries);
    
    if (!subQueries || !subQueries.length) {
      console.log('ChecklistLoading - No subQueries to display');
      return null;
    }
    
    console.log('ChecklistLoading - Rendering', subQueries.length, 'subQueries');
    
    return (
      <Box mt={2} className="sub-queries">
        <Typography variant="subtitle2" sx={{ color: 'var(--theme-primary)', mb: 1 }}>
          Breaking down into:
        </Typography>
        {subQueries.map((query, index) => (
          <Box 
            key={index} 
            className="sub-query" 
            sx={{ 
              '--index': index,
              opacity: 1, // Change opacity to 1 for visibility
              mb: 1
            }}
          >
            <Typography variant="body2" sx={{ color: '#ddd', ml: 3 }}>
              {index + 1}. {query}
            </Typography>
          </Box>
        ))}
      </Box>
    );
  };

  // Render detailed steps progress if available
  const renderDetailedSteps = () => {
    console.log('ChecklistLoading - processingUpdate:', processingUpdate);
    
    if (!processingUpdate || !processingUpdate.steps || processingUpdate.steps.length === 0) {
      console.log('ChecklistLoading - No detailed steps to display');
      return null;
    }
    
    console.log('ChecklistLoading - Rendering detailed steps');
    
    return (
      <Box mt={2}>
        <StepProgressTracker
          steps={processingUpdate.steps}
          currentStep={processingUpdate.current_step}
          completedSteps={processingUpdate.completed_steps || []}
          title={`${currentStage === 'retrieving_documents' ? 'Retrieval' : 'Generation'} Progress`}
        />
      </Box>
    );
  };
  
  return (
    <Paper elevation={3} className="checklist-loading" sx={{
      backgroundColor: 'var(--theme-secondary-opacity-high)',
      borderRadius: '12px',
      padding: '20px',
      width: '100%',
      maxWidth: '600px',
      margin: '0 auto',
      position: 'relative',
      overflow: 'hidden'
    }}>
      <style dangerouslySetInnerHTML={{ __html: `
        .checklist-loading .step {
          display: flex;
          margin-bottom: 20px;
          position: relative;
          transition: transform 0.5s ease, opacity 0.5s ease, filter 0.5s ease;
        }
        
        .checklist-loading .step.completed {
          transform: translateY(-8px);
          opacity: 0.6;
          filter: blur(1.5px);
        }
        
        .checklist-loading .step-content {
          margin-left: 15px;
          padding-left: 10px;
          flex: 1;
        }
        
        .checklist-loading .step-icon {
          position: relative;
          z-index: 2;
          background: var(--theme-secondary);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
        }
        
        .checklist-loading .step-connector {
          position: absolute;
          left: 14px;
          top: 28px;
          bottom: -20px;
          width: 2px;
          background: var(--theme-secondary-opacity-medium);
          z-index: 1;
          transition: background-color 0.3s ease;
        }
        
        .checklist-loading .step.completed .step-connector {
          background: var(--theme-primary);
          opacity: 0.6;
        }
        
        .checklist-loading .step:last-child .step-connector {
          display: none;
        }
        
        .checklist-loading .step-title {
          font-weight: 500;
          transition: color 0.3s ease;
        }
        
        .checklist-loading .step.current .step-title {
          color: var(--theme-primary);
        }
        
        .checklist-loading .step-description {
          font-size: 0.85rem;
          color: var(--theme-text-secondary);
        }
        
        .checklist-loading .current-message {
          color: var(--theme-primary);
          font-weight: 500;
          margin-top: 20px;
          padding: 10px;
          border-top: 1px solid var(--theme-primary-opacity-low);
          animation: pulse 2s infinite ease-in-out;
        }
        
        .checklist-loading .progress-bar {
          height: 4px;
          width: 60%;
          margin: 6px 0;
          border-radius: 2px;
          background-color: var(--theme-primary-opacity-low);
          overflow: hidden;
          position: relative;
        }
        
        .checklist-loading .progress-bar-inner {
          position: absolute;
          height: 100%;
          left: 0;
          top: 0;
          background-color: var(--theme-primary);
          animation: progressAnimation 2s infinite ease-in-out;
        }
        
        .checklist-loading .sub-queries {
          margin-top: 15px;
          opacity: 0;
          animation: fadeIn 0.5s ease 0.2s forwards;
        }
        
        .checklist-loading .sub-query {
          animation: slideIn 0.5s ease forwards;
          animation-delay: calc(0.2s + (var(--index) * 0.15s));
        }
        
        @keyframes pulse {
          0% { opacity: 0.7; }
          50% { opacity: 1; }
          100% { opacity: 0.7; }
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
      `}} />
      
      {/* Main checklist steps */}
      <Box className="checklist-steps">
        {steps.map((step, index) => (
          <Box 
            key={index}
            className={`step ${isStepCompleted(step.stage) ? 'completed' : ''} ${currentStage === step.stage ? 'current' : ''}`}
          >
            {getStepIcon(step, index)}
            <div className="step-connector"></div>
            
            <Box className="step-content">
              <Typography className="step-title" variant="subtitle2" color="#fff">
                {step.title}
              </Typography>
              <Typography className="step-description" variant="body2">
                {step.description}
              </Typography>
              
              {currentStage === step.stage && (
                <Box className="progress-bar">
                  <Box className="progress-bar-inner"></Box>
                </Box>
              )}
              
              {/* Show sub-queries visualization if this is the splitting stage */}
              {currentStage === 'splitting_query' && step.stage === 'splitting_query' && renderSubQueries()}
              
              {/* Show detailed step progress for current stage */}
              {currentStage === step.stage && 
               (step.stage === 'retrieving_documents' || step.stage === 'generating_answer') && 
               renderDetailedSteps()}
            </Box>
          </Box>
        ))}
      </Box>
      
      {/* Current operation message */}
      {message && (
        <Typography className="current-message">
          {message}
        </Typography>
      )}
    </Paper>
  );
};

export default ChecklistLoading; 