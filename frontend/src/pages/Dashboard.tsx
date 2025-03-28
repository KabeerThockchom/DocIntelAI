import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, 
  Typography, 
  Grid, 
  Paper, 
  Button, 
  Card, 
  CardContent, 
  CardActions,
  Divider,
  Tooltip
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import ChatIcon from '@mui/icons-material/Chat';
import SearchIcon from '@mui/icons-material/Search';
import BarChartIcon from '@mui/icons-material/BarChart';

// Chart colors (using theme variables)
const colors = {
  primary: 'var(--theme-primary)', // Theme primary color
  secondary: 'var(--theme-secondary)', // Theme secondary color
  accent1: 'var(--theme-primary)', // Theme primary color
  accent2: 'var(--ey-medium-gray)', // EY Medium Gray
  accent3: 'var(--ey-light-gray)', // EY Light Gray
};

// Function to generate random number between min and max
const randomBetween = (min: number, max: number) => {
  return Math.floor(Math.random() * (max - min + 1) + min);
};

// This creates a subtle color variation for the cards
const getRandomColorVariation = (index: number) => {
  const randomBetween = (min: number, max: number) => Math.floor(Math.random() * (max - min + 1) + min);
  return index % 2 === 0 
    ? `var(--theme-primary-opacity-low)` // Theme primary with lower opacity
    : `var(--theme-secondary-opacity-low)`; // Theme secondary with lower opacity
};

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const blobsCreated = useRef(false);

  // Setup advanced lava lamp animation effect
  useEffect(() => {
    if (blobsCreated.current || !containerRef.current) return;
    
    // Create and inject CSS for the lava lamp animation
    const style = document.createElement('style');
    style.textContent = `
      .lava-container {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        overflow: hidden;
        filter: url('#dashboard-goo-effect');
        opacity: 0.9;
        z-index: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
      }
      
      .lava-blob {
        position: absolute;
        border-radius: 50%;
        z-index: 1;
        transform-origin: center center;
        will-change: transform;
        background-image: linear-gradient(-206deg, var(--theme-primary-light) 0%, var(--theme-primary) 100%);
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
      }
      
      .lava-blob.top {
        border-radius: 50%;
        width: 100%;
        height: 4%;
        top: -3%;
        left: 0;
        z-index: 1;
      }
      
      .lava-blob.bottom {
        border-radius: 50%;
        width: 100%;
        height: 4.5%;
        bottom: -3%;
        left: 0;
        z-index: 1;
      }
      
      @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(var(--float-y)); }
      }
      
      @keyframes size-pulse {
        0% { transform: scale(1); }
        33% { transform: scale(var(--scale-min)); }
        66% { transform: scale(var(--scale)); }
        100% { transform: scale(1); }
      }
      
      @keyframes wobble {
        0% { border-radius: 50%; }
        50% { border-radius: 42% 58% 70% 30% / 45% 45% 55% 55%; }
        100% { border-radius: 38% 52% 75% 36% / 50% 40% 50% 60%; }
      }
      
      @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
      
      .lava-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        opacity: 0.3;
        background: linear-gradient(
          45deg,
          transparent 0%,
          var(--theme-primary-opacity-low) 35%,
          var(--theme-primary-opacity-medium) 50%,
          var(--theme-primary-opacity-low) 65%,
          transparent 100%
        );
        animation: rotate 20s linear infinite;
      }
    `;
    document.head.appendChild(style);
    
    // Create SVG filter for the goo effect
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('version', '1.1');
    svg.style.position = 'absolute';
    svg.style.width = '0';
    svg.style.height = '0';
    
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    
    const filter = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
    filter.setAttribute('id', 'dashboard-goo-effect');
    
    const feGaussianBlur = document.createElementNS('http://www.w3.org/2000/svg', 'feGaussianBlur');
    feGaussianBlur.setAttribute('in', 'SourceGraphic');
    feGaussianBlur.setAttribute('stdDeviation', '10');
    feGaussianBlur.setAttribute('result', 'blur');
    
    const feColorMatrix = document.createElementNS('http://www.w3.org/2000/svg', 'feColorMatrix');
    feColorMatrix.setAttribute('in', 'blur');
    feColorMatrix.setAttribute('mode', 'matrix');
    feColorMatrix.setAttribute('values', '1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -7');
    feColorMatrix.setAttribute('result', 'goo');
    
    const feBlend = document.createElementNS('http://www.w3.org/2000/svg', 'feBlend');
    feBlend.setAttribute('in', 'SourceGraphic');
    feBlend.setAttribute('in2', 'goo');
    
    filter.appendChild(feGaussianBlur);
    filter.appendChild(feColorMatrix);
    filter.appendChild(feBlend);
    defs.appendChild(filter);
    svg.appendChild(defs);
    
    document.body.appendChild(svg);
    
    // CSS reference must match the filter ID
    style.textContent = style.textContent.replace('filter: url(\'#goo\')', 'filter: url(\'#dashboard-goo-effect\')');
    
    // Create multiple blobs with different animations
    const container = containerRef.current;
    const numBlobs = 8; // Number of regular blobs
    
    // Add overlay for additional movement effect
    const overlay = document.createElement('div');
    overlay.className = 'lava-overlay';
    container.appendChild(overlay);
    
    // Add top and bottom blobs for the lava lamp effect
    const topBlob = document.createElement('div');
    topBlob.className = 'lava-blob top';
    topBlob.style.backgroundImage = `linear-gradient(-206deg, var(--theme-primary-light) 0%, var(--theme-primary) 100%)`;
    container.appendChild(topBlob);
    
    const bottomBlob = document.createElement('div');
    bottomBlob.className = 'lava-blob bottom';
    bottomBlob.style.backgroundImage = `linear-gradient(-206deg, var(--theme-primary-light) 0%, var(--theme-primary) 100%)`;
    container.appendChild(bottomBlob);
    
    // Create specific sized blobs with defined animations
    const blobConfigs = [
      { width: 200, height: 200, left: '35%', bottom: '-15%', floatY: -600, animDuration: 18 },
      { width: 330, height: 330, right: '24%', bottom: '-65%', floatY: -420, animDuration: 22 },
      { width: 150, height: 150, left: '34%', bottom: '-15%', floatY: -305, animDuration: 16 },
      { width: 235, height: 235, left: '30%', bottom: '-19%', floatY: -465, animDuration: 16 },
      { width: 55, height: 55, left: '34%', bottom: '-25%', floatY: -700, animDuration: 32 },
      { width: 35, height: 35, right: '34%', bottom: '-25%', floatY: -700, animDuration: 12 },
      { width: 435, height: 435, right: '40%', bottom: '-85%', floatY: -300, animDuration: 32 },
      { width: 180, height: 180, left: '45%', bottom: '-35%', floatY: -500, animDuration: 20 }
    ];
    
    blobConfigs.forEach((config, i) => {
      const blob = document.createElement('div');
      blob.className = 'lava-blob';
      
      // Apply styles
      blob.style.width = `${config.width}px`;
      blob.style.height = `${config.height}px`;
      
      if (config.left) blob.style.left = config.left;
      if (config.right) blob.style.right = config.right;
      blob.style.bottom = config.bottom;
      
      // Alternate colors for variety
      const scaleMax = (randomBetween(120, 180) / 100).toFixed(2);
      const scaleMin = (randomBetween(60, 90) / 100).toFixed(2);
      const wobbleDuration = randomBetween(4, 10);
      
      // Background gradient with theme colors
      blob.style.backgroundImage = i % 2 === 0 
        ? `linear-gradient(-206deg, var(--theme-primary-opacity-low) 0%, var(--theme-primary) 100%)`
        : `linear-gradient(-206deg, var(--theme-secondary-opacity-low) 0%, var(--theme-secondary) 100%)`;
      
      // Set animations
      blob.style.animation = `
        wobble ${wobbleDuration}s ease-in-out alternate infinite,
        float ${config.animDuration}s ease-in-out infinite
      `;
      
      // Set CSS variables for animations
      blob.style.setProperty('--float-y', `${config.floatY}%`);
      blob.style.setProperty('--scale', scaleMax);
      blob.style.setProperty('--scale-min', scaleMin);
      
      container.appendChild(blob);
    });
    
    // Create a few smaller, faster-moving bubbles
    for (let i = 0; i < 4; i++) {
      const tinyBlob = document.createElement('div');
      tinyBlob.className = 'lava-blob';
      
      const size = randomBetween(30, 80);
      const left = randomBetween(20, 80);
      const bottom = randomBetween(-30, -10);
      const floatY = randomBetween(-500, -300);
      const duration = randomBetween(8, 15);
      
      tinyBlob.style.width = `${size}px`;
      tinyBlob.style.height = `${size}px`;
      tinyBlob.style.left = `${left}%`;
      tinyBlob.style.bottom = `${bottom}%`;
      
      // Background gradient that matches the theme
      tinyBlob.style.backgroundImage = i % 2 === 0 
        ? `linear-gradient(-206deg, var(--theme-primary-light) 0%, var(--theme-primary) 100%)`
        : `linear-gradient(-206deg, var(--theme-secondary-light) 0%, var(--theme-secondary) 100%)`;
      
      // Set animations
      tinyBlob.style.animation = `
        wobble ${randomBetween(3, 6)}s ease-in-out alternate infinite,
        float ${duration}s ease-in-out infinite
      `;
      
      // Set CSS variables for animations
      tinyBlob.style.setProperty('--float-y', `${floatY}%`);
      
      container.appendChild(tinyBlob);
    }
    
    blobsCreated.current = true;
    
    // Clean up
    return () => {
      document.head.removeChild(style);
      if (document.body.contains(svg)) {
        document.body.removeChild(svg);
      }
      if (containerRef.current) {
        while (containerRef.current.firstChild) {
          containerRef.current.removeChild(containerRef.current.firstChild);
        }
      }
      blobsCreated.current = false;
    };
  }, []);

  const cards = [
    {
      title: 'Documents',
      description: 'Upload, view, and manage your documents from local storage and Google Drive',
      icon: <DescriptionIcon fontSize="large" sx={{ color: colors.primary }} />,
      action: () => navigate('/documents'),
      buttonText: 'View Documents',
      gradient: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primary} 100%)`,
      color: colors.primary,
    },
    {
      title: 'Chat',
      description: 'Chat with your documents using AI',
      icon: <ChatIcon fontSize="large" sx={{ color: colors.primary }} />,
      action: () => navigate('/chat'),
      buttonText: 'Start Chatting',
      gradient: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primary} 100%)`,
      color: colors.primary,
    },
    {
      title: 'Search',
      description: 'Search across all your documents',
      icon: <SearchIcon fontSize="large" sx={{ color: colors.primary }} />,
      action: () => navigate('/search'),
      buttonText: 'Search Documents',
      gradient: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primary} 100%)`,
      color: colors.primary,
    },
    {
      title: 'Statistics',
      description: 'View system statistics and analytics',
      icon: <BarChartIcon fontSize="large" sx={{ color: colors.primary }} />,
      action: () => navigate('/statistics'),
      buttonText: 'View Statistics',
      gradient: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primary} 100%)`,
      color: colors.primary,
    }
  ];

  return (
    <Box>
      <Paper 
        elevation={0} 
        sx={{ 
          p: 4,
          mb: 4, 
          background: 'transparent', // Remove background to show lava lamp
          color: 'var(--ey-white)',
          position: 'relative',
          overflow: 'hidden',
          minHeight: '350px', // Increased height for better lava lamp effect
          zIndex: 0, // Ensure proper stacking context
          '&::before': { // Add background as pseudo-element under the lava lamp
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: `linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-primary) 100%)`,
            zIndex: -1
          }
        }}
      >
        {/* Advanced lava lamp container */}
        <Box
          component="div"
          className="lava-container" 
          ref={containerRef}
          sx={{ 
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 0
          }}
        />
        
        {/* Dark overlay to improve text readability */}
        <Box 
          sx={{ 
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'var(--theme-secondary-opacity-low)', // Use theme CSS variable
            zIndex: 1,
          }}
        />
        
        <Box sx={{ position: 'relative', zIndex: 2 }}>
          <Typography 
            variant="h3" 
            gutterBottom 
            sx={{ 
              fontWeight: 700,
              textShadow: `0 2px 4px var(--theme-secondary-opacity-low)`,
              color: '#ffffff',
            }}
          >
            Welcome to docintel
          </Typography>
          <Typography 
            variant="h6" 
            sx={{ 
              mb: 4,
              opacity: 0.9,
              maxWidth: 600,
              lineHeight: 1.5,
              textShadow: `0 1px 2px var(--theme-secondary-opacity-low)`,
              color: '#ffffff',
            }}
          >
            A powerful tool for processing, analyzing, and chatting with your documents using AI. 
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Tooltip title="Upload and manage your documents">
              <Button 
                variant="contained" 
                onClick={() => navigate('/documents/upload')}
                sx={{ 
                  bgcolor: 'white',
                  color: '#333333',
                  '&:hover': {
                    bgcolor: 'rgba(255, 255, 255, 0.9)',
                  },
                  px: 4,
                  py: 1.5,
                  boxShadow: '0 4px 6px rgba(51, 51, 51, 0.2)',
                }}
              >
                Upload Documents
              </Button>
            </Tooltip>
            <Tooltip title="Start chatting with your documents using AI">
              <Button 
                variant="outlined" 
                onClick={() => navigate('/chat')}
                sx={{ 
                  borderColor: 'white',
                  color: 'white',
                  '&:hover': {
                    borderColor: 'rgba(255, 255, 255, 0.9)',
                    bgcolor: 'rgba(255, 255, 255, 0.1)',
                  },
                  px: 4,
                  py: 1.5,
                  boxShadow: '0 4px 6px rgba(51, 51, 51, 0.2)',
                }}
              >
                Start Chatting
              </Button>
            </Tooltip>
          </Box>
        </Box>
      </Paper>

      <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Quick Access
      </Typography>
      
      <Grid container spacing={3}>
        {cards.map((card, index) => (
          <Grid item xs={12} sm={6} md={4} key={card.title}>
            <Card 
              sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                position: 'relative',
                overflow: 'hidden',
                transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: `0 8px 16px -2px var(--theme-primary-opacity-low)`,
                },
                borderTop: `4px solid ${index % 2 === 0 ? colors.primary : colors.primary}`,
              }}
            >
              <CardContent sx={{ flexGrow: 1, p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  {card.icon}
                  <Typography 
                    variant="h6" 
                    component="div" 
                    sx={{ 
                      ml: 2,
                      fontWeight: 600,
                      color: card.color,
                    }}
                  >
                    {card.title}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {card.description}
                </Typography>
                <Tooltip title={`Click to ${card.buttonText.toLowerCase()}`}>
                  <Button 
                    size="large" 
                    onClick={card.action}
                    sx={{ 
                      mt: 'auto',
                      color: card.color,
                      '&:hover': {
                        bgcolor: `${card.color}10`,
                      },
                    }}
                  >
                    {card.buttonText}
                  </Button>
                </Tooltip>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default Dashboard; 