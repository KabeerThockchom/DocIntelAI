import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  IconButton,
  Divider,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  CircularProgress,
  Alert,
  Tooltip
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { chatService, ChatSessionCreate } from '../../services/chatService';
import { formatDistanceToNow } from 'date-fns';
import { useAuth } from '../../context/AuthContext';
import ChatIcon from '@mui/icons-material/Chat';

const ChatSessions: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [newSessionTitle, setNewSessionTitle] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const { user } = useAuth();

  // Query for getting chat sessions - user_id is included in auth headers automatically
  const { data, isLoading, error } = useQuery({
    queryKey: ['chatSessions'],
    queryFn: () => chatService.listChatSessions(),
  });

  // Mutation for creating a new chat session
  const createMutation = useMutation({
    mutationFn: (sessionData: ChatSessionCreate) => {
      return chatService.createChatSession(sessionData);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
      setCreateDialogOpen(false);
      setNewSessionTitle('');
      navigate(`/chat/${data.session_id}`);
    }
  });

  // Mutation for deleting a chat session
  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => {
      return chatService.deleteChatSession(sessionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
      setDeleteDialogOpen(false);
      setSessionToDelete(null);
    }
  });

  const handleCreateSession = () => {
    if (!newSessionTitle.trim()) return;
    
    createMutation.mutate({
      title: newSessionTitle.trim(),
      user_id: user?.id || 'anonymous', // Use authenticated user ID or fallback to anonymous
      metadata: {
        created_from: 'web_interface',
        // Include any other metadata that might be useful
      }
    });
  };

  const handleDeleteSession = (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setSessionToDelete(sessionId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (sessionToDelete) {
      deleteMutation.mutate(sessionToDelete);
    }
  };

  const handleSessionClick = (sessionId: string) => {
    navigate(`/chat/${sessionId}`);
  };

  return (
    <Box>
      <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4">
            Chat Sessions
          </Typography>
          <Tooltip title="Create a new chat session">
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              New Chat
            </Button>
          </Tooltip>
        </Box>
        <Typography variant="body1" color="text.secondary">
          Start a new chat or continue an existing conversation
        </Typography>
      </Paper>

      <Paper sx={{ p: 3 }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress sx={{ color: 'var(--theme-primary)' }} />
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            Error loading chat sessions
          </Alert>
        ) : data?.sessions.length === 0 ? (
          <Box 
            sx={{ 
              display: 'flex', 
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              py: 4,
              backgroundColor: 'var(--theme-background)',
              borderRadius: 2,
              border: '1px solid var(--theme-border)',
              animation: 'fadeIn 0.8s ease-in-out'
            }}
          >
            <ChatIcon 
              sx={{ 
                fontSize: 60, 
                color: 'var(--theme-primary)', 
                mb: 2,
                animation: 'pulse 2s infinite ease-in-out'
              }} 
            />
            <Typography 
              variant="h6" 
              sx={{ 
                color: 'var(--theme-text-primary)',
                mb: 1,
                fontWeight: 500
              }}
            >
              You don't have any chat sessions yet
            </Typography>
            <Typography 
              variant="body2" 
              sx={{ 
                color: 'var(--theme-text-secondary)',
                mb: 3
              }}
            >
              Click "New Chat" to get started with your document conversations
            </Typography>
            <Button
              variant="contained"
              sx={{
                backgroundColor: 'var(--theme-primary)',
                color: 'var(--theme-primary-contrast)',
                '&:hover': {
                  backgroundColor: 'var(--theme-primary-dark)',
                }
              }}
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              New Chat
            </Button>
          </Box>
        ) : (
          <List>
            {data?.sessions.map((session, index) => (
              <React.Fragment key={session.session_id}>
                {index > 0 && <Divider component="li" />}
                <ListItem
                  secondaryAction={
                    <IconButton 
                      edge="end" 
                      aria-label="delete"
                      onClick={(e) => handleDeleteSession(session.session_id, e)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  }
                  disablePadding
                >
                  <ListItemButton onClick={() => handleSessionClick(session.session_id)}>
                    <ListItemText 
                      primary={session.title} 
                      secondary={`Updated ${formatDistanceToNow(new Date(session.updated_at))} ago`}
                    />
                  </ListItemButton>
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        )}
      </Paper>

      {/* Create Session Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
        <DialogTitle>New Chat Session</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Enter a title for your new chat session.
          </DialogContentText>
          <TextField
            autoFocus
            margin="dense"
            id="title"
            label="Chat Title"
            type="text"
            fullWidth
            variant="outlined"
            value={newSessionTitle}
            onChange={(e) => setNewSessionTitle(e.target.value)}
            InputProps={{
              placeholder: 'e.g., Project Research, Technical Support, etc.'
            }}
          />
        </DialogContent>
        <DialogActions>
          <Tooltip title="Cancel creation of new chat">
            <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          </Tooltip>
          <Tooltip title={!newSessionTitle.trim() || createMutation.isPending ? "Chat title is required" : "Create new chat session"}>
            <span> {/* Wrapper for disabled button */}
              <Button 
                onClick={handleCreateSession} 
                disabled={!newSessionTitle.trim() || createMutation.isPending}
                variant="contained"
              >
                {createMutation.isPending ? <CircularProgress size={24} /> : 'Create'}
              </Button>
            </span>
          </Tooltip>
        </DialogActions>
      </Dialog>

      {/* Delete Session Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Chat Session</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this chat session? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Tooltip title="Cancel deletion">
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          </Tooltip>
          <Tooltip title={deleteMutation.isPending ? "Delete in progress" : "Permanently delete this chat session"}>
            <span> {/* Wrapper for disabled button */}
              <Button 
                onClick={handleDeleteConfirm} 
                color="error"
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? <CircularProgress size={24} /> : 'Delete'}
              </Button>
            </span>
          </Tooltip>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ChatSessions; 