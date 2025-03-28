import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Tooltip,
  ListItemButton
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import DescriptionIcon from '@mui/icons-material/Description';
import ChatIcon from '@mui/icons-material/Chat';
import SearchIcon from '@mui/icons-material/Search';
import BarChartIcon from '@mui/icons-material/BarChart';
import { useThemeContext } from '../../context/ThemeContext';

interface SidebarProps {
  onItemClick?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onItemClick }) => {
  const { darkMode, currentTheme } = useThemeContext();
  
  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
    { text: 'Documents', icon: <DescriptionIcon />, path: '/documents' },
    { text: 'Chat', icon: <ChatIcon />, path: '/chat' },
    { text: 'Search', icon: <SearchIcon />, path: '/search' },
    { text: 'Statistics', icon: <BarChartIcon />, path: '/statistics' },
  ];

  // Determine text color based on current theme and dark mode
  const getTextColor = () => {
    if (darkMode) {
      return 'var(--ey-white)';
    } else {
      return 'var(--theme-secondary)';
    }
  };

  return (
    <>
      <List sx={{ px: 2 }}>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ mb: 1 }}>
            <ListItemButton
              component={NavLink}
              to={item.path}
              onClick={onItemClick}
              sx={{
                borderRadius: 2,
                '&.active': {
                  backgroundColor: 'var(--theme-primary)',
                  '& .MuiListItemIcon-root': {
                    color: currentTheme === 'ey' || currentTheme === 'nvidia' 
                      ? 'var(--theme-secondary)' 
                      : 'var(--ey-white)',
                  },
                  '& .MuiListItemText-root': {
                    color: currentTheme === 'ey' || currentTheme === 'nvidia' 
                      ? 'var(--theme-secondary)' 
                      : 'var(--ey-white)',
                  },
                  '& .MuiListItemText-root .MuiTypography-root': {
                    color: currentTheme === 'ey' || currentTheme === 'nvidia' 
                      ? 'var(--theme-secondary)' 
                      : 'var(--ey-white)',
                    fontWeight: 600,
                  },
                  '&:hover': {
                    backgroundColor: 'var(--theme-primary)',
                  },
                },
                '&:hover': {
                  backgroundColor: 'var(--theme-primary-opacity-low)',
                },
                transition: 'all 0.2s ease-in-out',
              }}
            >
              <Tooltip title={item.text} placement="right">
                <ListItemIcon 
                  sx={{ 
                    minWidth: 40,
                    color: getTextColor(),
                  }}
                >
                  {item.icon}
                </ListItemIcon>
              </Tooltip>
              <ListItemText 
                primary={item.text} 
                primaryTypographyProps={{
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  color: getTextColor(),
                }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider sx={{ mx: 2, backgroundColor: 'var(--theme-secondary-opacity-low)' }} />
    </>
  );
};

export default Sidebar; 