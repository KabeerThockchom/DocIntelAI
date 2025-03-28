import React from 'react';
import { 
  Box, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  SelectChangeEvent,
  useTheme,
  IconButton,
  Tooltip
} from '@mui/material';
import { useThemeContext, ThemeType } from '../context/ThemeContext';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';

const ThemeSwitcher: React.FC = () => {
  const { darkMode, toggleDarkMode, currentTheme, setTheme } = useThemeContext();
  const theme = useTheme();

  const handleThemeChange = (event: SelectChangeEvent) => {
    setTheme(event.target.value as ThemeType);
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <Tooltip title={darkMode ? "Switch to light mode" : "Switch to dark mode"}>
        <IconButton 
          onClick={toggleDarkMode} 
          color="inherit"
          aria-label="toggle dark mode"
        >
          {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
        </IconButton>
      </Tooltip>
      
      <FormControl size="small" sx={{ minWidth: 120 }}>
        <InputLabel id="theme-select-label">Theme</InputLabel>
        <Select
          labelId="theme-select-label"
          id="theme-select"
          value={currentTheme}
          label="Theme"
          onChange={handleThemeChange}
          sx={{
            '& .MuiSelect-select': {
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }
          }}
        >
          <MenuItem value="ey">
            <Box 
              sx={{ 
                width: 16, 
                height: 16, 
                borderRadius: '50%', 
                bgcolor: 'var(--theme-primary)',
                border: '1px solid var(--theme-primary-dark)'
              }} 
            />
            EY
          </MenuItem>
          <MenuItem value="apple">
            <Box 
              sx={{ 
                width: 16, 
                height: 16, 
                borderRadius: '50%', 
                bgcolor: 'var(--apple-blue)',
                border: '1px solid var(--apple-dark-gray)'
              }} 
            />
            Apple
          </MenuItem>
          <MenuItem value="nvidia">
            <Box 
              sx={{ 
                width: 16, 
                height: 16, 
                borderRadius: '50%', 
                bgcolor: 'var(--nvidia-green)',
                border: '1px solid var(--nvidia-black)'
              }} 
            />
            Nvidia
          </MenuItem>
          <MenuItem value="vanguard">
            <Box 
              sx={{ 
                width: 16, 
                height: 16, 
                borderRadius: '50%', 
                bgcolor: 'var(--vanguard-red)',
                border: '1px solid var(--vanguard-black)'
              }} 
            />
            Vanguard
          </MenuItem>
        </Select>
      </FormControl>
    </Box>
  );
};

export default ThemeSwitcher; 