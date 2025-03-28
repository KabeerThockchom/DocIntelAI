import React from 'react';
import { Box, Typography } from '@mui/material';
import { ReactComponent as LogoSVG } from '../../icons/DocuIntelLogo.svg';

interface LogoProps {
  variant?: 'full' | 'icon' | 'text';
  size?: number;
  color?: string;
}

const Logo: React.FC<LogoProps> = ({ 
  variant = 'full', 
  size = 32,
  color
}) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center' }}>
      {(variant === 'full' || variant === 'icon') && (
        <LogoSVG width={size} height={size} style={{ marginRight: variant === 'full' ? 8 : 0 }} />
      )}
      
      {(variant === 'full' || variant === 'text') && (
        <Typography 
          variant="h6" 
          component="div"
          sx={{ 
            fontWeight: 700,
            background: 'linear-gradient(45deg, var(--theme-secondary) 30%, var(--theme-secondary-dark) 90%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '0.5px',
            fontSize: size * 0.75 + 'px',
            textShadow: '0 1px 2px var(--theme-primary-opacity-low)',
            lineHeight: 1,
          }}
        >
          docintel
        </Typography>
      )}
    </Box>
  );
};

export default Logo; 