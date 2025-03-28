import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Typography,
  Container,
  keyframes,
  useTheme,
  Grid,
  Paper,
  Fade,
  Zoom,
  Card,
  CardContent,
  CardActions,
} from '@mui/material';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import LockIcon from '@mui/icons-material/Lock';
import ChatIcon from '@mui/icons-material/Chat';
import SearchIcon from '@mui/icons-material/Search';
import DescriptionIcon from '@mui/icons-material/Description';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import StorageIcon from '@mui/icons-material/Storage';

// Keyframes for animations
const typewriter = keyframes`
  from {
    width: 0;
  }
  to {
    width: var(--typewriter-width);
  }
`;

const blinkCursor = keyframes`
  from, to { border-right-color: transparent; }
  50% { border-right-color: #fff; }
`;

const moveInCircle = keyframes`
  0% {
    transform: rotate(0deg);
  }
  50% {
    transform: rotate(180deg);
  }
  100% {
    transform: rotate(360deg);
  }
`;

const moveVertical = keyframes`
  0% {
    transform: translateY(-50%);
  }
  50% {
    transform: translateY(50%);
  }
  100% {
    transform: translateY(-50%);
  }
`;

const moveHorizontal = keyframes`
  0% {
    transform: translateX(-50%) translateY(-10%);
  }
  50% {
    transform: translateX(50%) translateY(10%);
  }
  100% {
    transform: translateX(-50%) translateY(-10%);
  }
`;

const iconRotate = keyframes`
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
`;

const float = keyframes`
  0% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
  100% {
    transform: translateY(0px);
  }
`;

const pulse = keyframes`
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
`;

// Feature cards information (clean up duplicates and use consistent styling)
const features = [
  {
    title: "Document Management",
    description: "Upload, organize, and find documents with ease. Our platform handles various formats.",
    icon: <InsertDriveFileIcon sx={{ fontSize: 40, color: 'var(--ey-yellow)' }} />,
    delay: 200,
  },
  {
    title: "Intelligent Search",
    description: "Find exactly what you need with semantic search across all your documents",
    icon: <SearchIcon sx={{ fontSize: 40, color: 'var(--ey-dark-gray)' }} />,
    delay: 400,
  },
  {
    title: "Chat with Documents",
    description: "Ask questions and get answers directly from your document knowledge base",
    icon: <ChatIcon sx={{ fontSize: 40, color: 'var(--ey-yellow)' }} />,
    delay: 600,
  },
];

const Home: React.FC = () => {
  const navigate = useNavigate();
  const theme = useTheme();
  const [isAnimationComplete, setIsAnimationComplete] = useState(false);
  const [isButtonHovered, setIsButtonHovered] = useState(false);
  const [showFeatures, setShowFeatures] = useState(false);
  const textRef = useRef<HTMLDivElement>(null);
  const [previousTextWidth, setPreviousTextWidth] = useState<number | null>(null);
  const text = "Welcome to docintel";

  // Calculate animation duration based on text length
  const typingSpeed = 75; // ms per character
  const typingDuration = text.length * typingSpeed;

  useEffect(() => {
    // Function to calculate and set the typewriter width
    const calculateTypewriterWidth = () => {
      if (textRef.current) {
        // Create temporary element to measure text width
        const tempElement = document.createElement('div');
        tempElement.style.position = 'absolute';
        tempElement.style.visibility = 'hidden';
        tempElement.style.whiteSpace = 'nowrap';
        tempElement.style.fontSize = window.innerWidth < 600 ? '1.8rem' : window.innerWidth < 960 ? '3rem' : '4rem';
        tempElement.style.fontWeight = '700';
        tempElement.style.fontFamily = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
        tempElement.innerText = text;
        document.body.appendChild(tempElement);
        
        // Set the width as a CSS variable
        const width = tempElement.offsetWidth;
        document.documentElement.style.setProperty('--typewriter-width', `${width}px`);
  
        // Clean up
        document.body.removeChild(tempElement);
      }
    };

    // Calculate typewriter width initially and when window is resized
    calculateTypewriterWidth();
    window.addEventListener('resize', calculateTypewriterWidth);

    const timer = setTimeout(() => {
      setIsAnimationComplete(true);
    }, typingDuration);

    const featuresTimer = setTimeout(() => {
      setShowFeatures(true);
    }, typingDuration + 500);

    return () => {
      clearTimeout(timer);
      clearTimeout(featuresTimer);
      window.removeEventListener('resize', calculateTypewriterWidth);
    };
  }, [typingDuration, text]);

  const handleUnlock = () => {
    navigate('/login');
  };

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100vw',
        height: '100vh',
        overflow: 'auto',
        background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.95), rgba(0, 0, 0, 0.9))',
      }}
    >
      {/* Animated gradient background */}
      <Box
        sx={{
          position: 'fixed',
          width: '100%',
          height: '100%',
          overflow: 'hidden',
          filter: 'blur(60px)',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            background: `radial-gradient(circle at center, var(--ey-yellow) 0, rgba(255, 230, 9, 0.8) 60%)`,
            mixBlendMode: 'soft-light',
            width: '70%',
            height: '70%',
            top: 'calc(50% - 35%)',
            left: 'calc(50% - 35%)',
            animation: `${moveVertical} 25s ease infinite`,
            opacity: 0.7,
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            background: `radial-gradient(circle at center, var(--ey-yellow) 0, var(--ey-yellow) 60%)`,
            mixBlendMode: 'soft-light',
            width: '60%',
            height: '60%',
            top: 'calc(50% - 30%)',
            left: 'calc(50% - 30%)',
            animation: `${moveInCircle} 20s reverse infinite`,
            opacity: 0.6,
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            background: `radial-gradient(circle at 30% 70%, var(--ey-yellow) 0, var(--ey-yellow) 60%)`,
            mixBlendMode: 'soft-light',
            width: '50%',
            height: '50%',
            top: 'calc(50% - 25%)',
            left: 'calc(50% - 25%)',
            animation: `${moveHorizontal} 30s linear infinite`,
            opacity: 0.5,
          }}
        />
      </Box>

      {/* Main Content Container */}
      <Container
        maxWidth="lg"
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          position: 'relative',
          zIndex: 2,
          pt: 4,
        }}
      >
        {/* Hero Section */}
        <Box
          sx={{
            textAlign: 'center',
            my: 4,
            position: 'relative',
          }}
        >
          {/* Hidden text to calculate width */}
          <div ref={textRef} style={{ position: 'absolute', visibility: 'hidden' }}>
            {text}
          </div>

          {/* Animated Title */}
          <Typography
            variant="h1"
            component="h1"
            sx={{
              color: 'var(--ey-dark-gray)',
              fontWeight: 700,
              fontSize: { xs: '2rem', sm: '3rem', md: '4rem' },
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              borderRight: '4px solid',
              borderRightColor: 'var(--ey-yellow)',
              margin: '0 auto',
              letterSpacing: '-0.02em',
              lineHeight: 1.2,
              animation: `
                ${typewriter} ${typingDuration}ms steps(${text.length}, end) forwards,
                ${blinkCursor} 750ms step-end infinite
              `,
              display: 'inline-block',
            }}
          >
            {text}
          </Typography>

          {/* Subtitle */}
          <Fade in={isAnimationComplete} timeout={1000}>
            <Typography
              variant="h5"
              sx={{
                color: 'var(--ey-dark-gray)',
                mt: 2,
                fontWeight: 400,
                maxWidth: '700px',
                mx: 'auto',
                opacity: isAnimationComplete ? 1 : 0,
                transition: 'opacity 0.5s',
              }}
            >
              Unlock insights from your documents with powerful AI assistance
            </Typography>
          </Fade>
        </Box>

        {/* Features Grid */}
        <Grid 
          container 
          spacing={3} 
          sx={{ 
            mt: 4,
            mb: 6,
            opacity: showFeatures ? 1 : 0,
            transition: 'opacity 0.8s ease-in-out',
          }}
        >
          {features.map((feature, index) => (
            <Grid item xs={12} md={4} key={index}>
              <Zoom 
                in={showFeatures} 
                style={{ 
                  transitionDelay: showFeatures ? `${feature.delay}ms` : '0ms',
                  transitionDuration: '500ms'
                }}
              >
                <Card
                  className="ey-bg-dark fadeIn"
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    p: 2,
                    transition: 'transform 0.3s, box-shadow 0.3s',
                    borderRadius: '8px',
                    border: '1px solid var(--ey-medium-gray)',
                    '&:hover': {
                      transform: 'translateY(-8px)',
                      boxShadow: '0 10px 20px rgba(0,0,0,0.2)',
                    },
                  }}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box
                      sx={{
                        display: 'flex',
                        justifyContent: 'center',
                        mb: 2,
                        animation: `${float} 3s ease-in-out infinite`,
                      }}
                    >
                      {feature.icon}
                    </Box>
                    <Typography 
                      variant="h5" 
                      component="h2" 
                      gutterBottom
                      align="center"
                      sx={{ 
                        fontWeight: 600,
                        color: 'var(--ey-white)',
                      }}
                    >
                      {feature.title}
                    </Typography>
                    <Typography 
                      variant="body1" 
                      align="center"
                      sx={{ 
                        color: 'var(--ey-light-gray)',
                      }}
                    >
                      {feature.description}
                    </Typography>
                  </CardContent>
                </Card>
              </Zoom>
            </Grid>
          ))}
        </Grid>

        {/* Call-to-action button */}
        <Box
          sx={{
            textAlign: 'center',
            mt: 2,
            opacity: isAnimationComplete ? 1 : 0,
            transition: 'opacity 0.5s ease-in',
            transitionDelay: '0.3s',
          }}
        >
          <Button
            variant="contained"
            className="ey-bg-yellow"
            size="large"
            startIcon={isButtonHovered ? <LockOpenIcon /> : <LockIcon />}
            onClick={handleUnlock}
            onMouseEnter={() => setIsButtonHovered(true)}
            onMouseLeave={() => setIsButtonHovered(false)}
            sx={{
              px: 4,
              py: 1.5,
              borderRadius: '30px',
              fontWeight: 600,
              boxShadow: '0 4px 10px rgba(0,0,0,0.15)',
              textTransform: 'none',
              fontSize: '1.1rem',
              color: 'var(--ey-dark-gray)',
              backgroundColor: 'var(--ey-yellow)',
              transition: 'all 0.3s ease',
              opacity: isAnimationComplete ? 1 : 0,
              '&:hover': {
                backgroundColor: 'var(--ey-yellow)',
                boxShadow: '0 6px 15px rgba(0,0,0,0.2)',
                transform: 'scale(1.05)'
              },
            }}
          >
            Get Started
          </Button>
        </Box>

      </Container>
    </Box>
  );
};

export default Home; 