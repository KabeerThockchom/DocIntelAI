import React, { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { 
  Box, 
  CssBaseline, 
  Drawer, 
  AppBar, 
  Toolbar, 
  Typography, 
  Divider, 
  IconButton,
  useTheme,
  useMediaQuery,
  Avatar,
  Menu,
  MenuItem,
  ListItemIcon,
  Tooltip,
  Button
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import LogoutIcon from '@mui/icons-material/Logout';
import PersonIcon from '@mui/icons-material/Person';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import Sidebar from './Sidebar';
import { useAuth } from '../../context/AuthContext';
import { useThemeContext } from '../../context/ThemeContext';
import ThemeSwitcher from '../ThemeSwitcher';

const drawerWidth = 240;

const AppLayout: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [open, setOpen] = useState(!isMobile);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const { darkMode, toggleDarkMode, currentTheme } = useThemeContext();

  // For the user menu
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const menuOpen = Boolean(anchorEl);

  const handleDrawerOpen = () => {
    setOpen(true);
  };

  const handleDrawerClose = () => {
    setOpen(false);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    handleMenuClose();
    await signOut();
    navigate('/login');
  };

  // Logo and App Name Component
  const Logo = () => (
    <Tooltip title="Go to Dashboard" arrow placement="right">
      <Box 
        sx={{ 
          display: 'flex', 
          alignItems: 'center',
          cursor: 'pointer',
          '&:hover': {
            opacity: 0.85,
          },
          transition: 'opacity 0.2s ease'
        }}
        onClick={() => navigate('/')}
        aria-label="Go to Dashboard"
      >
        <AutoAwesomeIcon 
          sx={{ 
            color: 'var(--theme-primary)', 
            mr: 1,
            fontSize: '28px',
            transition: 'color 0.3s ease'
          }} 
        />
        <Typography 
          variant="h6" 
          noWrap 
          component="div"
          sx={{ 
            fontWeight: 700,
            background: `linear-gradient(45deg, var(--theme-primary) 30%, var(--theme-primary) 90%)`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '0.5px',
            fontSize: '1.5rem',
            transition: 'background 0.3s ease'
          }}
        >
          docintel
        </Typography>
      </Box>
    </Tooltip>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          zIndex: theme.zIndex.drawer + 1,
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          backgroundColor: darkMode ? 'var(--theme-secondary)' : 'var(--ey-white)',
          color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
          boxShadow: 'none',
          borderBottom: '1px solid',
          borderColor: darkMode ? 'var(--theme-primary-opacity-low)' : 'var(--theme-secondary-opacity-low)',
          width: '100%',
          ...(open && {
            marginLeft: drawerWidth,
            width: `calc(100% - ${drawerWidth}px)`,
            transition: theme.transitions.create(['width', 'margin'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          }),
        }}
      >
        <Toolbar sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              onClick={handleDrawerOpen}
              edge="start"
              sx={{
                marginRight: 2,
                ...(open && { display: 'none' }),
              }}
            >
              <MenuIcon />
            </IconButton>
            
            {/* Show logo in AppBar only when drawer is closed */}
            {!open && <Logo />}
          </Box>
          
          {/* User Actions Area */}
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {/* Theme Switcher */}
            <ThemeSwitcher />
            
            {/* User Profile Menu */}
            <Tooltip title="Account settings">
              <IconButton
                onClick={handleMenuOpen}
                size="small"
                aria-controls={menuOpen ? 'account-menu' : undefined}
                aria-haspopup="true"
                aria-expanded={menuOpen ? 'true' : undefined}
                sx={{ ml: 2 }}
              >
                {user?.user_metadata?.avatar_url ? (
                  <Avatar 
                    src={user.user_metadata.avatar_url} 
                    alt={user.email?.substring(0, 1) || '?'} 
                    sx={{ width: 32, height: 32 }}
                  />
                ) : (
                  <Avatar sx={{ width: 32, height: 32, bgcolor: 'var(--theme-primary)' }}>
                    {user?.email?.substring(0, 1)?.toUpperCase() || '?'}
                  </Avatar>
                )}
              </IconButton>
            </Tooltip>
            <Menu
              anchorEl={anchorEl}
              id="account-menu"
              open={menuOpen}
              onClose={handleMenuClose}
              onClick={handleMenuClose}
              PaperProps={{
                elevation: 0,
                sx: {
                  overflow: 'visible',
                  filter: 'drop-shadow(0px 2px 8px var(--theme-secondary-opacity-low))',
                  mt: 1.5,
                  minWidth: 200,
                  backgroundColor: darkMode ? 'var(--theme-secondary)' : 'var(--ey-white)',
                  color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
                  border: '1px solid',
                  borderColor: darkMode ? 'var(--theme-primary-opacity-low)' : 'var(--theme-secondary-opacity-low)',
                  '& .MuiAvatar-root': {
                    width: 32,
                    height: 32,
                    ml: -0.5,
                    mr: 1,
                  },
                },
              }}
              transformOrigin={{ horizontal: 'right', vertical: 'top' }}
              anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            >
              <Box sx={{ px: 2, py: 1 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {user?.email}
                </Typography>
              </Box>
              <Divider />
              <MenuItem onClick={toggleDarkMode}>
                <ListItemIcon>
                  {darkMode ? <Brightness7Icon fontSize="small" /> : <Brightness4Icon fontSize="small" />}
                </ListItemIcon>
                {darkMode ? 'Light Mode' : 'Dark Mode'}
              </MenuItem>
              <MenuItem onClick={handleLogout}>
                <ListItemIcon>
                  <LogoutIcon fontSize="small" />
                </ListItemIcon>
                Sign Out
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>
      
      {/* Drawer component - Fixed the variant to ensure it can be closed */}
      <Drawer
        variant={isMobile ? "temporary" : "temporary"}
        open={open}
        onClose={handleDrawerClose}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            borderRight: '1px solid',
            borderColor: darkMode ? 'var(--theme-primary-opacity-low)' : 'var(--theme-secondary-opacity-low)',
            backgroundColor: darkMode ? 'var(--theme-secondary)' : 'var(--ey-white)',
            color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
            boxShadow: 'none',
            transition: 'background-color 0.3s ease, color 0.3s ease',
          },
          display: { xs: open ? 'block' : 'none', sm: open ? 'block' : 'none' }
        }}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
      >
        <Toolbar
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: [1],
            minHeight: '64px',
          }}
        >
          {/* Logo in sidebar */}
          <Logo />
          
          <IconButton onClick={handleDrawerClose} sx={{ color: 'inherit' }}>
            <ChevronLeftIcon />
          </IconButton>
        </Toolbar>
        <Divider />
        <Sidebar onItemClick={handleDrawerClose} />
      </Drawer>
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: '100%',
          marginTop: '64px',
          backgroundColor: darkMode ? 'var(--theme-secondary-opacity-low)' : 'var(--ey-white)',
          color: darkMode ? 'var(--ey-white)' : 'var(--theme-secondary)',
          minHeight: '100vh',
          transition: 'background-color 0.3s ease, color 0.3s ease',
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
};

export default AppLayout; 