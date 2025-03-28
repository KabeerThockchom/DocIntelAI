import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  CircularProgress,
  Alert,
  IconButton,
  Divider,
  Tooltip,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SendIcon from '@mui/icons-material/Send';
import DownloadIcon from '@mui/icons-material/Download';
import InfoIcon from '@mui/icons-material/Info';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import DescriptionIcon from '@mui/icons-material/Description';
import chatService, { ProcessingStage, ProcessingUpdate, MessageResponse, Citation } from '../../services/chatService';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import ProcessingSteps from '../../components/ProcessingSteps';
import QuerySplitVisualizer from '../../components/QuerySplitVisualizer';
import { useSnackbar } from 'notistack';
import ChecklistLoading from '../../components/ChecklistLoading';

// Markdown styling
const markdownStyles = {
  p: { mt: 1, mb: 1 },
  h1: { mt: 2, mb: 1, fontSize: '1.7rem', fontWeight: 'bold' },
  h2: { mt: 2, mb: 1, fontSize: '1.5rem', fontWeight: 'bold' },
  h3: { mt: 2, mb: 1, fontSize: '1.3rem', fontWeight: 'bold' },
  h4: { mt: 2, mb: 1, fontSize: '1.2rem', fontWeight: 'bold' },
  h5: { mt: 2, mb: 1, fontSize: '1.1rem', fontWeight: 'bold' },
  h6: { mt: 2, mb: 1, fontSize: '1rem', fontWeight: 'bold' },
  ul: { pl: 4, mt: 1, mb: 1 },
  ol: { pl: 4, mt: 1, mb: 1 },
  li: { mt: 0.5, mb: 0.5 },
  pre: {
    mt: 1,
    mb: 1,
    borderRadius: 1,
    overflow: 'hidden',
    '& > div': {
      borderRadius: 1,
      margin: '0 !important',
    }
  },
  code: {
    backgroundColor: 'background.default',
    p: 0.5,
    borderRadius: 0.5,
    fontFamily: 'monospace',
    fontSize: '0.875rem'
  },
  blockquote: {
    pl: 2,
    borderLeft: '4px solid',
    borderColor: 'divider',
    fontStyle: 'italic',
    my: 1
  },
  a: { color: 'primary.main' },
  img: {
    maxWidth: '100%',
    height: 'auto'
  }
};

interface CitationDialogProps {
  open: boolean;
  onClose: () => void;
  citation: Citation | null;
}

const CitationDialog: React.FC<CitationDialogProps> = ({ open, onClose, citation }) => {
  const navigate = useNavigate();
  
  if (!citation) return null;
  
  const handleViewInDocument = () => {
    if (!citation) return;
    
    // Navigate to document viewer with chunk and page number information
    navigate(`/documents/${citation.document_id}/view`, {
      state: {
        chunkId: citation.chunk_id,
        pageNumber: citation.page_number || 1
      }
    });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Citation Source</DialogTitle>
      <DialogContent>
        <Typography variant="subtitle1" gutterBottom>
          {citation.document_name}
          {citation.page_number && ` - Page ${citation.page_number}`}
        </Typography>
        <Paper 
          variant="outlined" 
          sx={{ 
            p: 2, 
            backgroundColor: 'background.default',
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap',
            fontSize: '0.875rem',
            mt: 2
          }}
        >
          {citation.text_snippet}
        </Paper>
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Document ID: {citation.document_id}
          </Typography>
          <br />
          <Typography variant="caption" color="text.secondary">
            Chunk ID: {citation.chunk_id}
          </Typography>
          <br />
          <Typography variant="caption" color="text.secondary">
            Relevance Score: {citation.relevance_score.toFixed(2)}
          </Typography>
          <br />
          <Typography variant="caption" color="text.secondary">
            {citation.is_cited === false ? 'Additional source (not directly cited)' : 'Directly cited in response'}
          </Typography>
        </Box>
      </DialogContent>
      <DialogActions>
        <Tooltip title="View this text in the original document">
          <Button 
            onClick={handleViewInDocument}
            color="primary"
            variant="outlined"
            startIcon={<DescriptionIcon />}
          >
            View in Document
          </Button>
        </Tooltip>
        <Tooltip title="Close this dialog">
          <Button onClick={onClose}>Close</Button>
        </Tooltip>
      </DialogActions>
    </Dialog>
  );
};

// Custom component to render markdown with hoverable citations
const MarkdownWithCitations: React.FC<{ 
  content: string; 
  citations: Citation[];
  onCitationHover: (citation: Citation) => void;
}> = ({ content, citations, onCitationHover }) => {
  const navigate = useNavigate();
  
  // Create a map of citation numbers to citation objects
  const citationMap = new Map<number, Citation>();
  
  // Find citation markers like [1], [2], etc. and replace with hoverable spans
  const processedContent = content.replace(/\[(\d+)\]/g, (match, citationNumber) => {
    const num = parseInt(citationNumber, 10);
    if (num > 0 && num <= citations.length) {
      const citation = citations[num - 1];
      if (citation) {
        citationMap.set(num, citation);
        return `[CITATION_MARKER_${num}]`;
      }
    }
    return match;
  });

  // Split the content by citation markers
  const parts = processedContent.split(/\[CITATION_MARKER_(\d+)\]/);
  
  // Handle direct navigation to document
  const handleViewInDocument = (citation: Citation) => {
    navigate(`/documents/${citation.document_id}/view`, {
      state: {
        chunkId: citation.chunk_id,
        pageNumber: citation.page_number || 1
      }
    });
  };
  
  // Custom renderers for markdown components
  const renderers = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <SyntaxHighlighter
          style={atomDark}
          language={match[1]}
          PreTag="div"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    table({ node, children, ...props }: any) {
      return (
        <Box sx={{ overflowX: 'auto', width: '100%', mb: 2 }}>
          <table style={{ 
            width: '100%', 
            borderCollapse: 'collapse', 
            tableLayout: 'fixed'
          }} {...props}>{children}</table>
        </Box>
      );
    },
    thead({ node, children, ...props }: any) {
      return <thead style={{ backgroundColor: 'var(--mui-palette-background-default)' }} {...props}>{children}</thead>;
    },
    th({ node, children, ...props }: any) {
      return <th style={{ 
        padding: '8px 12px', 
        borderBottom: '2px solid var(--mui-palette-divider)',
        textAlign: 'left',
        fontWeight: 'bold',
        whiteSpace: 'nowrap'
      }} {...props}>{children}</th>;
    },
    td({ node, children, ...props }: any) {
      return <td style={{ 
        padding: '8px 12px', 
        borderBottom: '1px solid var(--mui-palette-divider)',
        borderRight: '1px solid var(--mui-palette-divider)',
        textAlign: 'left'
      }} {...props}>{children}</td>;
    }
  };
  
  // Render the content with hoverable citations
  return (
    <Box sx={markdownStyles}>
      {parts.map((part, index) => {
        if (index % 2 === 0) {
          // Regular text part
          return (
            <ReactMarkdown 
              key={index} 
              remarkPlugins={[remarkGfm]} 
              components={renderers}
            >
              {part}
            </ReactMarkdown>
          );
        } else {
          // Citation marker
          const citationNumber = parseInt(part, 10);
          const citation = citationMap.get(citationNumber);
          
          if (citation) {
            return (
              <Tooltip
                key={index}
                title={
                  <Box>
                    <Typography variant="body2">{citation.document_name}</Typography>
                    {citation.page_number && <Typography variant="body2">Page {citation.page_number}</Typography>}
                    <Typography variant="body2" sx={{ fontStyle: 'italic', mt: 1 }}>
                      "{citation.text_snippet.substring(0, 100)}..."
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                      <Typography variant="body2">
                        Click for details
                      </Typography>
                      <Tooltip title="View this text in the original document">
                        <Button 
                          size="small" 
                          variant="outlined" 
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewInDocument(citation);
                          }}
                          sx={{ ml: 1, minWidth: 'auto', p: '2px 8px' }}
                        >
                          View Source
                        </Button>
                      </Tooltip>
                    </Box>
                  </Box>
                }
                arrow
                placement="top"
                componentsProps={{
                  tooltip: {
                    sx: {
                      maxWidth: 'none',
                      p: 2
                    }
                  }
                }}
              >
                <Box
                  component="span"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCitationHover(citation);
                  }}
                  sx={{
                    backgroundColor: 'primary.light',
                    color: 'primary.contrastText',
                    borderRadius: '4px',
                    padding: '0 4px',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    '&:hover': {
                      backgroundColor: 'primary.main',
                    }
                  }}
                >
                  [{citationNumber}]
                </Box>
              </Tooltip>
            );
          }
          
          return <span key={index}>[{part}]</span>;
        }
      })}
    </Box>
  );
};

// Extend the ProcessingUpdate type to include completedStages
interface ExtendedProcessingUpdate extends ProcessingUpdate {
  completedStages?: ProcessingStage[];
}

// Get all stages before a given stage
const getEarlierStages = (stage: ProcessingStage): ProcessingStage[] => {
  const stages: ProcessingStage[] = ['analyzing_query', 'splitting_query', 'retrieving_documents', 'generating_answer'];
  const index = stages.indexOf(stage);
  return index > 0 ? stages.slice(0, index) : [];
};

const ChatDetail: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState('');
  const [processingStage, setProcessingStage] = useState<ExtendedProcessingUpdate | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [citationDialogOpen, setCitationDialogOpen] = useState(false);
  const [sourcesTabValue, setSourcesTabValue] = useState(0);
  const [contextMenuAnchor, setContextMenuAnchor] = useState<null | HTMLElement>(null);
  const [contextMenuCitation, setContextMenuCitation] = useState<Citation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [subQueries, setSubQueries] = useState<string[]>([]);
  const [originalQuery, setOriginalQuery] = useState<string>('');
  const [showQuerySplitVisualizer, setShowQuerySplitVisualizer] = useState<boolean>(false);
  const [previousQuery, setPreviousQuery] = useState<string>('');
  const [isFollowUp, setIsFollowUp] = useState<boolean>(false);
  const { enqueueSnackbar } = useSnackbar();
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  // Fetch chat session and history
  const { data: chatHistory, isLoading, error: queryError } = useQuery({
    queryKey: ['chatHistory', sessionId],
    queryFn: () => chatService.getChatHistory(sessionId!),
    enabled: !!sessionId,
    refetchInterval: false
  });

  // Function to send a new message
  const handleSendMessage = async () => {
    if (!message.trim() || !sessionId || isSending) {
      return;
    }

    try {
      setIsSending(true);
      // Save the original query for visualization
      setOriginalQuery(message);
      setSubQueries([]);
      setShowQuerySplitVisualizer(false);
      
      // Create a new message object
      const userMessage: MessageResponse = {
        message_id: `temp-${Date.now()}`,
        session_id: sessionId!,
        role: 'user',
        content: message.trim(),
        created_at: new Date().toISOString(),
        citations: [],
        metadata: {}
      };
      
      // Add the user message to the messages array
      queryClient.setQueryData(['chatHistory', sessionId], (oldData: any) => {
        if (!oldData) return oldData;
        return {
          ...oldData,
          messages: [...oldData.messages, userMessage]
        };
      });
      
      // Clear the input
      setMessage('');
      
      // Show initial processing stage
      setProcessingStage({
        stage: 'analyzing_query',
        message: 'Analyzing your question...',
        details: {},
        isCompleted: false,
        completedStages: []
      });
      
      try {
        console.log('Sending message with updates...');
        // Send the message with processing updates
        await chatService.sendMessageWithUpdates(
          sessionId!,
          { 
            content: userMessage.content,
            stream_processing: true, // Always enable streaming
            use_retrieval: true,
            include_history: true, // Always include chat history for context - CRITICAL for proper conversation
            metadata: {
              timestamp: Date.now(), // Add timestamp to help identify this message
              clientId: `client-${Date.now()}` // Add client ID to help track this message
            }
          },
          (update) => {
            // Process update immediately without any setTimeout
            handleProcessingUpdate(update);
            
            // Handle sub-queries if available
            if (update.stage === 'splitting_query') {
              // Check if update has subQueries directly
              if (update.subQueries && update.subQueries.length > 0) {
                setSubQueries(update.subQueries);
                setShowQuerySplitVisualizer(true);
                
                // Handle follow-up question context
                if (update.details?.isFollowUp) {
                  setIsFollowUp(true);
                  if (update.details?.previousQuery) {
                    setPreviousQuery(update.details.previousQuery);
                  }
                } else {
                  setIsFollowUp(false);
                  setPreviousQuery('');
                }
              }
            }
            
            // Clear the processing stage when complete
            if (update.stage === 'complete') {
              // Refresh the messages to get the final result
              queryClient.invalidateQueries({ queryKey: ['chatHistory', sessionId] });
            }
          }
        );
        
      } catch (error) {
        console.error('Error sending message:', error);
        enqueueSnackbar('Failed to send message', { variant: 'error' });
        
        // Clear any processing indicators
        setProcessingStage(null);
        
        // Allow user to try again
        setMessage(userMessage.content);
        
        // Remove the temporary user message
        queryClient.setQueryData(['chatHistory', sessionId], (oldData: any) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            messages: oldData.messages.filter((m: MessageResponse) => m.message_id !== userMessage.message_id)
          };
        });
      } finally {
        setIsSending(false);
      }
    } catch (error) {
      console.error('Error in handleSendMessage:', error);
      enqueueSnackbar('An unexpected error occurred', { variant: 'error' });
      setIsSending(false);
    }
  };

  // Export chat session mutation
  const exportMutation = useMutation({
    mutationFn: () => chatService.exportChatSession(sessionId!, true),
    onSuccess: (data) => {
      // Create a download link for the exported chat
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-session-${sessionId}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  });

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory]);

  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation);
    setCitationDialogOpen(true);
  };

  const handleSourcesTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setSourcesTabValue(newValue);
  };
  
  const handleContextMenu = (event: React.MouseEvent<HTMLDivElement>, citation: Citation) => {
    event.preventDefault();
    setContextMenuAnchor(event.currentTarget);
    setContextMenuCitation(citation);
  };
  
  const handleCloseContextMenu = () => {
    setContextMenuAnchor(null);
    setContextMenuCitation(null);
  };
  
  const handleViewInDocument = (citation: Citation) => {
    handleCloseContextMenu();
    
    // Navigate to document viewer with chunk and page number information
    navigate(`/documents/${citation.document_id}/view`, {
      state: {
        chunkId: citation.chunk_id,
        pageNumber: citation.page_number || 1
      }
    });
  };

  // Handle processing updates from API
  const handleProcessingUpdate = (update: ProcessingUpdate) => {
    console.log(`[HANDLER START] Processing update received:`, JSON.stringify(update));
    
    // Ensure isCompleted is a boolean
    const isCompletedBoolean = update.isCompleted === true;
    console.log(`[HANDLER] isCompleted converted to boolean:`, isCompletedBoolean);
    
    // If we're already at 'complete' stage, don't update anymore
    if (processingStage?.stage === 'complete') {
      console.log('[HANDLER] Ignoring update as we are already in complete stage');
      return;
    }
    
    console.log('[HANDLER] Current processingStage before update:', processingStage ? JSON.stringify(processingStage) : 'null');
    
    // Update processing state immediately
    setProcessingStage(prevState => {
      console.log('[HANDLER] Inside setState callback, prevState:', prevState ? JSON.stringify(prevState) : 'null');
      
      // If there's no previous state, use update directly with empty completedStages
      if (!prevState) {
        const newState = { 
          ...update, 
          isCompleted: isCompletedBoolean,
          completedStages: [] 
        };
        console.log('[HANDLER] No previous state, creating new state:', JSON.stringify(newState));
        return newState;
      }
      
      // Create a copy of the previous state to update
      const updatedState: ExtendedProcessingUpdate = { 
        ...prevState,
        stage: update.stage,
        message: update.message,
        details: update.details,
        isCompleted: isCompletedBoolean
      };
      
      console.log('[HANDLER] Created updated state (before completedStages):', JSON.stringify(updatedState));
      
      // Track completed stages in a separate array
      const completedStages: ProcessingStage[] = [...(prevState.completedStages || [])];
      console.log('[HANDLER] Current completedStages:', JSON.stringify(completedStages));
      
      // Mark previous stages as completed
      if (update.stage !== 'analyzing_query') {
        const earlierStages = getEarlierStages(update.stage);
        console.log('[HANDLER] Earlier stages for', update.stage, ':', JSON.stringify(earlierStages));
        
        earlierStages.forEach(stage => {
          if (!completedStages.includes(stage)) {
            console.log('[HANDLER] Adding earlier stage to completed:', stage);
            completedStages.push(stage);
          }
        });
      }
      
      // If the current stage is marked as completed, add it to completed stages
      if (isCompletedBoolean && !completedStages.includes(update.stage)) {
        console.log(`[HANDLER] Marking stage ${update.stage} as completed`);
        completedStages.push(update.stage);
      }
      
      // Store completed stages
      updatedState.completedStages = completedStages;
      console.log('[HANDLER] Final completedStages:', JSON.stringify(completedStages));
      
      // If we have subQueries, add them to the state
      if (update.subQueries && update.subQueries.length > 0) {
        console.log(`[HANDLER] Setting ${update.subQueries.length} subQueries`, JSON.stringify(update.subQueries));
        updatedState.subQueries = update.subQueries;
      }
      
      // Special handling for 'complete' stage
      if (update.stage === 'complete') {
        console.log('[HANDLER] Complete stage reached, updating all stages to completed');
        const allStages: ProcessingStage[] = ['analyzing_query', 'splitting_query', 'retrieving_documents', 'generating_answer'];
        updatedState.completedStages = allStages;
        
        // If there was an error, update UI accordingly
        if (update.details?.error) {
          console.log('[HANDLER] Error detected in update:', update.details.error);
          setError('Failed to process message');
        }
        
        // Clear processing state when complete immediately
        console.log('[HANDLER] Clearing processing state as stage is complete');
        setProcessingStage(null);
        setShowQuerySplitVisualizer(false);
      }
      
      console.log('[HANDLER] Final updated state:', JSON.stringify(updatedState));
      return updatedState;
    });
    
    console.log('[HANDLER END] Processing update handler complete');
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (queryError) {
    return (
      <Box>
        <Tooltip title="Return to chat sessions">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/chat')}
            sx={{ mb: 2 }}
          >
            Back to Chat Sessions
          </Button>
        </Tooltip>
        <Alert severity="error">
          Error loading chat session: {(queryError as Error).message}
        </Alert>
      </Box>
    );
  }

  if (!chatHistory) {
    return (
      <Box>
        <Tooltip title="Return to chat sessions">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/chat')}
            sx={{ mb: 2 }}
          >
            Back to Chat Sessions
          </Button>
        </Tooltip>
        <Alert severity="error">
          Chat session not found
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center' }}>
        <Tooltip title="Return to chat sessions list">
          <IconButton onClick={() => navigate('/chat')} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
        </Tooltip>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          {chatHistory?.title || 'Chat Session'}
        </Typography>
        <Box>
          <Tooltip title="Export chat session">
            <IconButton 
              onClick={() => exportMutation.mutate()}
              disabled={exportMutation.isPending}
            >
              {exportMutation.isPending ? <CircularProgress size={24} /> : <DownloadIcon />}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Messages area */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          bgcolor: 'background.default'
        }}
      >
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : queryError ? (
          <Alert severity="error">Error loading chat history</Alert>
        ) : (
          <>
            {chatHistory?.messages.map((msg) => (
              <Box
                key={msg.message_id}
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '80%',
                  minWidth: msg.role === 'user' ? 'auto' : '60%',
                }}
              >
                <Card 
                  sx={{ 
                    backgroundColor: msg.role === 'user' ? 'var(--theme-primary)' : 'background.default',
                    color: msg.role === 'user' ? '#333333' : 'text.primary'
                  }}
                >
                  <CardContent sx={{ pb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      {msg.role === 'user' ? (
                        <PersonIcon fontSize="small" sx={{ mr: 1 }} />
                      ) : (
                        <SmartToyIcon fontSize="small" sx={{ mr: 1 }} />
                      )}
                      <Typography variant="subtitle2">
                        {msg.role === 'user' ? 'You' : 'AI Assistant'}
                      </Typography>
                      <Typography variant="caption" sx={{ ml: 1, opacity: 0.7 }}>
                        {new Date(msg.created_at).toLocaleTimeString()}
                      </Typography>
                    </Box>
                    
                    {msg.role === 'user' ? (
                      <Typography variant="body1">{msg.content}</Typography>
                    ) : (
                      <MarkdownWithCitations 
                        content={msg.content} 
                        citations={msg.citations.filter(c => c.is_cited !== false)} 
                        onCitationHover={handleCitationClick}
                      />
                    )}
                    
                    {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Divider sx={{ mb: 1 }} />
                        
                        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                          <Tabs 
                            value={sourcesTabValue} 
                            onChange={handleSourcesTabChange}
                            variant="fullWidth"
                            sx={{ minHeight: '36px' }}
                          >
                            <Tab 
                              label={
                                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                  <CheckCircleIcon fontSize="small" sx={{ mr: 0.5 }} />
                                  <Typography variant="caption">Cited Sources</Typography>
                                </Box>
                              } 
                              sx={{ py: 0.5 }}
                            />
                            <Tab 
                              label={
                                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                  <HelpOutlineIcon fontSize="small" sx={{ mr: 0.5 }} />
                                  <Typography variant="caption">All Sources</Typography>
                                </Box>
                              }
                              sx={{ py: 0.5 }}
                            />
                          </Tabs>
                        </Box>
                        
                        <Box sx={{ mt: 1 }}>
                          {sourcesTabValue === 0 ? (
                            // Cited sources only
                            <Box>
                              {msg.citations.filter(c => c.is_cited !== false).length > 0 ? (
                                <Box sx={{ mt: 0.5 }}>
                                  {msg.citations
                                    .filter(c => c.is_cited !== false)
                                    .map((citation, index) => (
                                      <Chip
                                        key={citation.citation_id}
                                        label={`${index + 1}. ${citation.document_name}`}
                                        size="small"
                                        onClick={() => handleCitationClick(citation)}
                                        onContextMenu={(e) => handleContextMenu(e, citation)}
                                        sx={{ 
                                          mr: 0.5, 
                                          mb: 0.5, 
                                          cursor: 'pointer',
                                          backgroundColor: citation.is_cited === false ? 'background.paper' : 'primary.light',
                                          color: citation.is_cited === false ? 'text.primary' : 'primary.contrastText',
                                          border: citation.is_cited === false ? '1px dashed var(--theme-border)' : 'none',
                                          borderColor: 'divider',
                                          '&:hover': {
                                            backgroundColor: citation.is_cited === false ? 'action.hover' : 'primary.main',
                                            color: citation.is_cited === false ? 'text.primary' : 'primary.contrastText'
                                          }
                                        }}
                                      />
                                    ))}
                                </Box>
                              ) : (
                                <Typography variant="caption" color="text.secondary">
                                  No sources were directly cited in this response.
                                </Typography>
                              )}
                            </Box>
                          ) : (
                            // All sources including non-cited ones
                            <Box>
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                                All sources that were retrieved, including those not directly cited:
                              </Typography>
                              <Box sx={{ mt: 0.5 }}>
                                {msg.citations.map((citation, index) => (
                                  <Chip
                                    key={citation.citation_id}
                                    label={citation.document_name}
                                    size="small"
                                    onClick={() => handleCitationClick(citation)}
                                    onContextMenu={(e) => handleContextMenu(e, citation)}
                                    sx={{ 
                                      mr: 0.5, 
                                      mb: 0.5, 
                                      cursor: 'pointer',
                                      backgroundColor: citation.is_cited === false ? 'background.paper' : 'primary.light',
                                      color: citation.is_cited === false ? 'text.primary' : 'primary.contrastText',
                                      border: citation.is_cited === false ? '1px dashed var(--theme-border)' : 'none',
                                      borderColor: 'divider',
                                      '&:hover': {
                                        backgroundColor: citation.is_cited === false ? 'action.hover' : 'primary.main',
                                        color: citation.is_cited === false ? 'text.primary' : 'primary.contrastText'
                                      }
                                    }}
                                  />
                                ))}
                              </Box>
                            </Box>
                          )}
                        </Box>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Box>
            ))}

            {/* Processing animation - Enhanced display */}
            {processingStage && (
              <Box sx={{ 
                alignSelf: 'flex-start', 
                width: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                alignItems: 'center', 
                mt: 2,
                mb: 4
              }}>
                <Box sx={{ width: '100%', maxWidth: '650px' }}>
                  <ChecklistLoading 
                    currentStage={processingStage.stage}
                    completedStages={processingStage.completedStages || []}
                    message={processingStage.message || 'Processing your question...'}
                    subQueries={subQueries}
                    processingUpdate={processingStage}
                  />
                </Box>

                {/* Show the QuerySplitVisualizer when in splitting_query stage and subqueries available */}
                {showQuerySplitVisualizer && subQueries.length > 0 && 
                 processingStage.stage !== 'complete' && (
                  <Box sx={{ 
                    mt: 3, 
                    width: '100%', 
                    maxWidth: '750px',
                    backgroundColor: 'rgba(51, 51, 51, 0.7)',
                    borderRadius: 2,
                    p: 2,
                    border: '1px solid var(--theme-border)'
                  }}>
                    <QuerySplitVisualizer 
                      originalQuery={originalQuery}
                      subQueries={subQueries}
                      previousQuery={previousQuery}
                      isFollowUp={isFollowUp}
                    />
                  </Box>
                )}
              </Box>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </Box>

      {/* Message input */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            placeholder="Type your message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
            multiline
            maxRows={5}
            disabled={!!processingStage || isSending} // Disable during processing
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              }
            }}
          />
          <Tooltip title={(!message.trim() || !!processingStage || isSending) ? "Enter a message first" : "Send your message"}>
            <span> {/* Wrapper needed for disabled button */}
              <Button
                variant="contained"
                sx={{ 
                  borderRadius: 2,
                  backgroundColor: 'var(--theme-primary)',
                  color: 'var(--theme-primary-contrast)',
                  '&:hover': {
                    backgroundColor: 'var(--theme-primary-dark)',
                  },
                  '&:disabled': {
                    backgroundColor: 'var(--theme-primary-opacity-low)',
                    color: 'var(--theme-neutral-opacity-medium)'
                  }
                }}
                onClick={handleSendMessage}
                disabled={!message.trim() || !!processingStage || isSending} // Disable during processing
              >
                {isSending ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  <SendIcon />
                )}
              </Button>
            </span>
          </Tooltip>
        </Box>
      </Box>

      {/* Citation dialog */}
      <CitationDialog
        open={citationDialogOpen}
        onClose={() => setCitationDialogOpen(false)}
        citation={selectedCitation}
      />

      {/* Context menu */}
      <Menu
        open={Boolean(contextMenuAnchor)}
        onClose={handleCloseContextMenu}
        anchorEl={contextMenuAnchor}
      >
        <MenuItem onClick={() => contextMenuCitation && handleCitationClick(contextMenuCitation)}>
          <ListItemIcon>
            <InfoIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>View Details</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => contextMenuCitation && handleViewInDocument(contextMenuCitation)}>
          <ListItemIcon>
            <DescriptionIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>View in Document</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default ChatDetail; 