import React, { createContext, useContext, useEffect, useState } from 'react';
import { createTheme, ThemeProvider as MuiThemeProvider } from '@mui/material/styles';

// Define the theme types
export type ThemeType = 'ey' | 'apple' | 'nvidia' | 'vanguard';

// Define the type for the context value
type ThemeContextType = {
  darkMode: boolean;
  toggleDarkMode: () => void;
  currentTheme: ThemeType;
  setTheme: (theme: ThemeType) => void;
};

// Create the context with default values
const ThemeContext = createContext<ThemeContextType>({
  darkMode: false,
  toggleDarkMode: () => {},
  currentTheme: 'ey',
  setTheme: () => {},
});

// Create a custom hook to use the theme context
export const useThemeContext = () => useContext(ThemeContext);

// Define the props for the ThemeProvider component
type ThemeProviderProps = {
  children: React.ReactNode;
};

// Theme Color Palettes
const themeColors = {
  ey: {
    darkGray: '#333333',
    primary: '#ffe600',
    white: '#ffffff',
    lightGray: '#cccccc',
    mediumGray: '#999999',
  },
  apple: {
    darkGray: '#1d1d1f',
    primary: '#0071e3',
    white: '#ffffff',
    lightGray: '#f5f5f7',
    mediumGray: '#86868b',
    accent: '#ff2d55',
  },
  nvidia: {
    darkGray: '#333333',
    primary: '#76b900',
    white: '#ffffff',
    lightGray: '#e5e5e5',
    mediumGray: '#999999',
    black: '#000000',
  },
  vanguard: {
    darkGray: '#333333',
    primary: '#c10230',
    white: '#ffffff',
    lightGray: '#e5e5e5',
    mediumGray: '#999999',
    darkRed: '#7b0018',
  },
};

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  // Check if the user has a theme preference in localStorage
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    const savedMode = localStorage.getItem('darkMode');
    return savedMode === null ? true : savedMode === 'true';
  });

  // Check if the user has a theme color preference in localStorage
  const [currentTheme, setCurrentTheme] = useState<ThemeType>(() => {
    const savedTheme = localStorage.getItem('currentTheme') as ThemeType;
    // Validate that the saved theme is one of the valid options
    return Object.keys(themeColors).includes(savedTheme) ? savedTheme : 'ey';
  });
  
  // Get the current theme colors and ensure we have a valid fallback
  const colors = themeColors[currentTheme] || themeColors['ey'];

  // Create the theme based on the current mode and theme colors
  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
      primary: {
        main: colors.primary, // Theme primary color
        light: currentTheme === 'ey' ? '#fff59d' : 
              currentTheme === 'apple' ? '#5fb9ff' :
              currentTheme === 'nvidia' ? '#a0e53b' :
              '#ff5a7e', // Light version
        dark: currentTheme === 'ey' ? '#c7b800' : 
             currentTheme === 'apple' ? '#0051a2' :
             currentTheme === 'nvidia' ? '#588a00' :
             '#7b0018', // Dark version
        contrastText: currentTheme === 'ey' || currentTheme === 'nvidia' ? colors.darkGray : colors.white,
      },
      secondary: {
        main: colors.darkGray, // Dark gray as secondary color
        light: '#5c5c5c', // Lighter dark gray
        dark: '#1e1e1e', // Darker gray
        contrastText: colors.white, // Text on dark gray background
      },
      background: {
        default: darkMode ? colors.darkGray : colors.white,
        paper: darkMode ? '#424242' : colors.white,
      },
      text: {
        primary: darkMode ? colors.white : colors.darkGray,
        secondary: darkMode ? colors.lightGray : colors.mediumGray,
      },
      divider: darkMode ? colors.mediumGray : colors.lightGray,
      error: {
        main: '#f44336',
        light: '#e57373',
        dark: '#d32f2f',
      },
      warning: {
        main: '#ff9800',
        light: '#ffb74d',
        dark: '#f57c00',
      },
      info: {
        main: '#2196f3',
        light: '#64b5f6',
        dark: '#1976d2',
      },
      success: {
        main: '#4caf50',
        light: '#81c784',
        dark: '#388e3c',
      },
    },
    typography: {
      fontFamily: [
        'Inter',
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        'Roboto',
        '"Helvetica Neue"',
        'Arial',
        'sans-serif',
      ].join(','),
      h1: {
        fontWeight: 700,
        color: darkMode ? colors.white : colors.darkGray,
      },
      h2: {
        fontWeight: 700,
        color: darkMode ? colors.white : colors.darkGray,
      },
      h3: {
        fontWeight: 600,
        color: darkMode ? colors.white : colors.darkGray,
      },
      h4: {
        fontWeight: 600,
        color: darkMode ? colors.white : colors.darkGray,
      },
      h5: {
        fontWeight: 600,
        color: darkMode ? colors.white : colors.darkGray,
      },
      h6: {
        fontWeight: 600,
        color: darkMode ? colors.white : colors.darkGray,
      },
    },
    shape: {
      borderRadius: 8, // Slightly reduced border radius for more corporate look
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 4,
            textTransform: 'none',
            fontWeight: 500,
            padding: '8px 16px',
          },
          containedPrimary: {
            backgroundColor: colors.primary,
            color: currentTheme === 'ey' || currentTheme === 'nvidia' ? colors.darkGray : colors.white,
            '&:hover': {
              backgroundColor: currentTheme === 'ey' ? '#ffef62' :
                              currentTheme === 'apple' ? '#6fbfff' :
                              currentTheme === 'nvidia' ? '#b0e54b' :
                              '#ff6b8e',
            },
          },
          outlinedPrimary: {
            borderColor: colors.primary,
            color: darkMode ? colors.primary : currentTheme === 'ey' || currentTheme === 'nvidia' ? colors.darkGray : colors.white,
            '&:hover': {
              borderColor: currentTheme === 'ey' ? '#ffef62' :
                              currentTheme === 'apple' ? '#6fbfff' :
                              currentTheme === 'nvidia' ? '#b0e54b' :
                              '#ff6b8e',
              backgroundColor: currentTheme === 'ey' || currentTheme === 'nvidia' ? 'rgba(255, 230, 0, 0.08)' : 'rgba(255, 230, 0, 0.1)',
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            borderRadius: 8,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 4,
          },
          colorPrimary: {
            backgroundColor: colors.primary,
            color: currentTheme === 'ey' || currentTheme === 'nvidia' ? colors.darkGray : colors.white,
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              borderRadius: 4,
            },
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          colorPrimary: {
            backgroundColor: darkMode ? colors.darkGray : colors.white,
            color: darkMode ? colors.white : colors.darkGray,
          },
        },
      },
      MuiListItem: {
        styleOverrides: {
          root: {
            '&.Mui-selected': {
              backgroundColor: darkMode ? 'rgba(255, 230, 0, 0.2)' : 'rgba(255, 230, 0, 0.1)',
              '&:hover': {
                backgroundColor: darkMode ? 'rgba(255, 230, 0, 0.3)' : 'rgba(255, 230, 0, 0.2)',
              },
            },
          },
        },
      },
      MuiTabs: {
        styleOverrides: {
          indicator: {
            backgroundColor: colors.primary,
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            '&.Mui-selected': {
              color: darkMode ? colors.primary : currentTheme === 'ey' || currentTheme === 'nvidia' ? colors.darkGray : colors.white,
            },
          },
        },
      },
    },
  });

  // Function to toggle dark mode
  const toggleDarkMode = () => {
    setDarkMode((prevMode) => {
      const newMode = !prevMode;
      localStorage.setItem('darkMode', String(newMode));
      return newMode;
    });
  };

  // Function to set theme
  const setTheme = (theme: ThemeType) => {
    setCurrentTheme(theme);
    localStorage.setItem('currentTheme', theme);
    
    // Apply theme class to body element
    document.body.classList.remove('theme-ey', 'theme-apple', 'theme-nvidia', 'theme-vanguard');
    document.body.classList.add(`theme-${theme}`);
  };

  // Save the mode to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('darkMode', String(darkMode));
  }, [darkMode]);
  
  // Apply theme class on initial render and theme change
  useEffect(() => {
    document.body.classList.remove('theme-ey', 'theme-apple', 'theme-nvidia', 'theme-vanguard');
    document.body.classList.add(`theme-${currentTheme}`);
  }, [currentTheme]);

  return (
    <ThemeContext.Provider value={{ darkMode, toggleDarkMode, currentTheme, setTheme }}>
      <MuiThemeProvider theme={theme}>
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
}; 