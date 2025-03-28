import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Tabs,
  Tab,
  Divider,
  List,
  ListItem,
  ListItemText,
  Card,
  CardContent,
  Grid,
  Tooltip,
  IconButton
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import DescriptionIcon from '@mui/icons-material/Description';
import StorageIcon from '@mui/icons-material/Storage';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import DownloadIcon from '@mui/icons-material/Download';
import VisibilityIcon from '@mui/icons-material/Visibility';
import FindInPageIcon from '@mui/icons-material/FindInPage';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import { documentService, DocumentDetail as DocumentDetailType } from '../../services/documentService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`document-tabpanel-${index}`}
      aria-labelledby={`document-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
};

const DocumentDetail: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [isDownloading, setIsDownloading] = useState(false);

  const { data, isLoading, error } = useQuery<DocumentDetailType>({
    queryKey: ['document', documentId],
    queryFn: () => documentService.getDocumentDetails(documentId!, true),
    enabled: !!documentId
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleDownloadDocument = async () => {
    if (!data) return;
    
    try {
      setIsDownloading(true);
      const blob = await documentService.getDocumentFile(documentId!);
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary anchor element and trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading document:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleViewInDocument = (chunk: any) => {
    if (!chunk || !documentId) return;
    
    navigate(`/documents/${documentId}/view`, {
      state: {
        chunkId: chunk.chunk_id,
        pageNumber: chunk.metadata.page_number || 1
      }
    });
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Tooltip title="Return to documents list">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/documents')}
            sx={{ mb: 2 }}
          >
            Back to Documents
          </Button>
        </Tooltip>
        <Alert severity="error">
          Error loading document: {(error as Error).message}
        </Alert>
      </Box>
    );
  }

  if (!data) {
    return (
      <Box>
        <Tooltip title="Return to documents list">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/documents')}
            sx={{ mb: 2 }}
          >
            Back to Documents
          </Button>
        </Tooltip>
        <Alert severity="error">
          Document not found
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Tooltip title="Return to documents list">
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/documents')}
          sx={{ mb: 2 }}
        >
          Back to Documents
        </Button>
      </Tooltip>

      <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <DescriptionIcon fontSize="large" color="primary" sx={{ mr: 2 }} />
            <Typography variant="h4">
              {data.filename}
            </Typography>
          </Box>
          <Box>
            <Tooltip title="View document">
              <IconButton 
                color="primary" 
                onClick={() => navigate(`/documents/${documentId}/view`)}
                sx={{ mr: 1 }}
              >
                <VisibilityIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title={isDownloading ? 'Download in progress' : 'Download this document'}>
              <Button
                variant="contained"
                color="primary"
                startIcon={isDownloading ? <CircularProgress size={20} color="inherit" /> : <DownloadIcon />}
                onClick={handleDownloadDocument}
                disabled={isDownloading}
              >
                {isDownloading ? 'Downloading...' : 'Download'}
              </Button>
            </Tooltip>
          </Box>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Chip 
            label={data.document_type.toUpperCase()} 
            color="primary" 
            variant="outlined" 
            sx={{ mr: 1 }} 
          />
          <LocalOfferIcon 
            fontSize="small" 
            sx={{ mr: 1 }} 
          />
          {data.tags.map((tag: string) => (
            <Chip 
              key={tag} 
              label={tag} 
              sx={{ mr: 1 }} 
            />
          ))}
          {data.ocr_used && (
            <Chip 
              label="OCR" 
              color="secondary" 
              sx={{ mr: 1 }} 
            />
          )}
        </Box>
      </Paper>

      <Paper sx={{ mb: 4 }}>
        <Tabs 
          value={tabValue} 
          onChange={handleTabChange}
          variant="fullWidth"
        >
          <Tab label="Overview" />
          <Tab label="Chunks" />
          <Tab label="Metadata" />
        </Tabs>
        
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <StorageIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">
                      Chunks
                    </Typography>
                  </Box>
                  <Typography variant="h3">
                    {data.total_chunks}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total document chunks
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <CalendarTodayIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">
                      Created
                    </Typography>
                  </Box>
                  <Typography variant="body1">
                    {new Date(data.created_at).toLocaleDateString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {new Date(data.created_at).toLocaleTimeString()}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <DescriptionIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">
                      Document ID
                    </Typography>
                  </Box>
                  <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                    {data.document_id}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
        
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Document Chunks ({data.chunks?.length})
          </Typography>
          
          <List>
            {data.chunks?.map((chunk: any, index: number) => (
              <React.Fragment key={chunk.chunk_id}>
                {index > 0 && <Divider />}
                <ListItem alignItems="flex-start" sx={{ flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle2" component="div">
                      Chunk {index + 1}
                    </Typography>
                    <Box>
                      {chunk.metadata.page_number && (
                        <Chip 
                          label={`Page ${chunk.metadata.page_number}`} 
                          size="small" 
                          sx={{ mr: 1 }} 
                        />
                      )}
                      {chunk.metadata.is_ocr && (
                        <Chip 
                          label="OCR" 
                          size="small" 
                          color="secondary" 
                          sx={{ mr: 1 }}
                        />
                      )}
                      <Tooltip title="View this text in the original document">
                        <Button
                          size="small"
                          variant="outlined"
                          color="primary"
                          startIcon={<FindInPageIcon />}
                          onClick={() => handleViewInDocument(chunk)}
                        >
                          View in Document
                        </Button>
                      </Tooltip>
                    </Box>
                  </Box>
                  <Paper 
                    variant="outlined" 
                    sx={{ 
                      p: 2, 
                      width: '100%', 
                      backgroundColor: 'background.default',
                      fontFamily: 'monospace',
                      whiteSpace: 'pre-wrap',
                      fontSize: '0.875rem'
                    }}
                  >
                    {chunk.text}
                  </Paper>
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        </TabPanel>
        
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Document Metadata
          </Typography>
          
          <Grid container spacing={3}>
            {/* Created By */}
            {data.metadata && data.metadata.created_by && (
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle1" color="primary" gutterBottom>
                      Created By
                    </Typography>
                    <Typography variant="body1">
                      {data.metadata.created_by}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            )}
            
            {/* Tags */}
            {data.tags && data.tags.length > 0 && (
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle1" color="primary" gutterBottom>
                      Tags
                    </Typography>
                    <Box>
                      {data.tags.map((tag: string) => (
                        <Chip 
                          key={tag} 
                          label={tag} 
                          sx={{ mr: 1, mb: 1 }} 
                        />
                      ))}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}
            
            {/* Source Information */}
            {data.metadata && data.metadata.additional_metadata && data.metadata.additional_metadata.source && (
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle1" color="primary" gutterBottom>
                      Source
                    </Typography>
                    <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                      {data.metadata.additional_metadata.source.replace('_', ' ')}
                    </Typography>
                    {data.metadata.additional_metadata.import_date && (
                      <Typography variant="body2" color="text.secondary">
                        Imported on: {new Date(data.metadata.additional_metadata.import_date).toLocaleString()}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}
            
            {/* Document Type */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle1" color="primary" gutterBottom>
                    Document Type
                  </Typography>
                  <Typography variant="body1" sx={{ textTransform: 'uppercase' }}>
                    {data.document_type}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          
          {/* Raw Metadata */}
          <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
            Raw Metadata
          </Typography>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <pre style={{ margin: 0, overflow: 'auto' }}>
              {JSON.stringify(data.metadata, null, 2)}
            </pre>
          </Paper>
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default DocumentDetail; 