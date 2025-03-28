import React, { useEffect, useState, useRef } from 'react';
import { 
  Box, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText, 
  Collapse,
  LinearProgress,
  Typography,
  Paper,
  Fade,
  alpha
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import SyncIcon from '@mui/icons-material/Sync';
import { keyframes } from '@mui/system';

// Define animation for the current active step
const pulse = keyframes`
  0% {
    opacity: 0.6;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.05);
  }
  100% {
    opacity: 0.6;
    transform: scale(1);
  }
`;

interface StepProgressTrackerProps {
  steps: string[];
  currentStep?: string | null;
  completedSteps: string[];
  title: string;
}

const StepProgressTracker: React.FC<StepProgressTrackerProps> = ({ 
  steps, 
  currentStep, 
  completedSteps, 
  title 
}) => {
  const [expanded, setExpanded] = useState(true);
  const [enteredSteps, setEnteredSteps] = useState<string[]>([]);
  const prevPropsRef = useRef({ steps, currentStep, completedSteps });

  // Debug props changes
  useEffect(() => {
    const prevProps = prevPropsRef.current;
    
    // Check if any props have changed
    const stepsChanged = steps !== prevProps.steps;
    const currentStepChanged = currentStep !== prevProps.currentStep;
    const completedStepsChanged = 
      completedSteps.length !== prevProps.completedSteps.length || 
      completedSteps.some((step, i) => step !== prevProps.completedSteps[i]);
    
    if (stepsChanged || currentStepChanged || completedStepsChanged) {
      console.log('[StepProgressTracker] Props updated:');
      if (stepsChanged) console.log(' - steps changed:', JSON.stringify(steps));
      if (currentStepChanged) console.log(' - currentStep changed:', currentStep);
      if (completedStepsChanged) console.log(' - completedSteps changed:', JSON.stringify(completedSteps));
      
      // Update ref with new props
      prevPropsRef.current = { steps, currentStep, completedSteps };
    }
  }, [steps, currentStep, completedSteps]);

  // Track which steps have been entered to animate them
  useEffect(() => {
    if (currentStep && !enteredSteps.includes(currentStep)) {
      console.log('[StepProgressTracker] New step entered:', currentStep);
      setEnteredSteps(prev => [...prev, currentStep]);
    }
  }, [currentStep, enteredSteps]);

  // Calculate progress percentage
  const progress = steps.length > 0 
    ? (completedSteps.length / steps.length) * 100 
    : 0;

  console.log('[StepProgressTracker] Rendering with progress:', progress, '%');

  return (
    <Fade in={true}>
      <Paper 
        elevation={1}
        sx={{
          p: 1.5,
          borderRadius: '8px',
          backgroundColor: 'background.paper',
          mb: 2,
          border: '1px solid',
          borderColor: 'divider',
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        {/* Progress bar */}
        <LinearProgress 
          variant="determinate" 
          value={progress} 
          sx={{ 
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '3px',
            backgroundColor: alpha('var(--theme-primary)', 0.2),
            '& .MuiLinearProgress-bar': {
              backgroundColor: 'var(--theme-primary)',
            }
          }}
        />

        {/* Title with click to expand/collapse */}
        <Box 
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            cursor: 'pointer',
            mb: expanded ? 1 : 0
          }}
          onClick={() => setExpanded(!expanded)}
        >
          <Typography variant="subtitle2" fontWeight="medium">
            {title} ({completedSteps.length}/{steps.length})
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {expanded ? 'Click to collapse' : 'Click to expand'}
          </Typography>
        </Box>

        {/* Steps list */}
        <Collapse in={expanded}>
          <List dense disablePadding>
            {steps.map((step, index) => {
              const isCompleted = completedSteps.includes(step);
              const isActive = currentStep === step;
              const hasBeenEntered = enteredSteps.includes(step);

              return (
                <ListItem
                  key={index}
                  dense
                  sx={{
                    py: 0.5,
                    px: 1,
                    borderRadius: '4px',
                    backgroundColor: isActive 
                      ? alpha('var(--theme-primary)', 0.1) 
                      : 'transparent',
                    animation: isActive 
                      ? `${pulse} 2s infinite ease-in-out` 
                      : 'none',
                    opacity: hasBeenEntered || isCompleted ? 1 : 0.5,
                    transition: 'opacity 0.3s, background-color 0.3s'
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {isCompleted ? (
                      <CheckCircleIcon fontSize="small" color="success" />
                    ) : isActive ? (
                      <SyncIcon 
                        fontSize="small" 
                        sx={{ 
                          color: 'var(--theme-primary)',
                          animation: `${pulse} 1.5s infinite ease-in-out`
                        }} 
                      />
                    ) : (
                      <RadioButtonUncheckedIcon fontSize="small" color="disabled" />
                    )}
                  </ListItemIcon>
                  <ListItemText 
                    primary={step} 
                    primaryTypographyProps={{
                      variant: 'body2',
                      fontWeight: isActive ? 'medium' : 'regular',
                      color: isActive ? 'text.primary' : 'text.secondary'
                    }}
                  />
                </ListItem>
              );
            })}
          </List>
        </Collapse>
      </Paper>
    </Fade>
  );
};

export default StepProgressTracker; 