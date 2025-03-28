import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Pagination,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Grid,
  Tooltip,
  Tabs,
  Tab
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DownloadIcon from '@mui/icons-material/Download';
import CloudQueueIcon from '@mui/icons-material/CloudQueue';
import DescriptionIcon from '@mui/icons-material/Description';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { documentService, DocumentSummary } from '../../services/documentService';
import DriveIntegration from '../drive/DriveIntegration';

interface DocumentListResponse {
  documents: DocumentSummary[];
  pagination: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`document-tabpanel-${index}`}
      aria-labelledby={`document-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ pt: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `document-tab-${index}`,
    'aria-controls': `document-tabpanel-${index}`,
  };
}

const DocumentList: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [documentType, setDocumentType] = useState<string>('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<string | null>(null);
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  // Read tab parameter from URL and handle OAuth code
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const tabParam = urlParams.get('tab');
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    
    // If there's an OAuth code, set tab to Google Drive (index 1)
    if (code) {
      console.log('OAuth code detected in URL, setting Drive tab');
      setTabValue(1);
      
      // Keep the code parameter for the DriveIntegration component to process
      // but remove any other parameters except state which is needed for OAuth
      const params = new URLSearchParams();
      params.set('code', code);
      if (state) params.set('state', state);
      
      // Keep the URL as is to allow DriveIntegration to process the code
      // window.history.replaceState({}, document.title, `${window.location.pathname}?${params.toString()}`);
    } 
    // Otherwise, handle the tab parameter as before
    else if (tabParam) {
      const tabIndex = parseInt(tabParam, 10);
      if (!isNaN(tabIndex) && tabIndex >= 0 && tabIndex <= 1) {
        setTabValue(tabIndex);
        
        // Remove the tab parameter from the URL to keep it clean
        // but only after we've processed it
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('tab');
        window.history.replaceState({}, document.title, newUrl.toString());
      }
    }
  }, [location]);

  const { data, isLoading, error } = useQuery<DocumentListResponse>({
    queryKey: ['documents', page, pageSize, documentType],
    queryFn: () => documentService.listDocuments(documentType, page, pageSize),
    enabled: tabValue === 0 // Only fetch when on the "My Documents" tab
  });

  const deleteMutation = useMutation<any, Error, string>({
    mutationFn: (documentId: string) => documentService.deleteDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setDeleteDialogOpen(false);
      setDocumentToDelete(null);
      // Show success notification
      alert('Document successfully deleted');
    },
    onError: (error) => {
      console.error('Error deleting document:', error);
      // Show error notification
      alert(`Failed to delete document: ${error.message}`);
      setDeleteDialogOpen(false);
      setDocumentToDelete(null);
    }
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    
    // Update URL to reflect the current tab without causing a page reload
    const newUrl = new URL(window.location.href);
    if (newValue === 1) {
      newUrl.searchParams.set('tab', '1');
    } else {
      newUrl.searchParams.delete('tab');
    }
    window.history.replaceState({}, document.title, newUrl.toString());
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  const handlePageSizeChange = (event: SelectChangeEvent<number>) => {
    setPageSize(event.target.value as number);
    setPage(1); // Reset to first page when changing page size
  };

  const handleDocumentTypeChange = (event: SelectChangeEvent) => {
    setDocumentType(event.target.value);
    setPage(1); // Reset to first page when changing filter
  };

  const handleDeleteClick = (documentId: string) => {
    setDocumentToDelete(documentId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (documentToDelete) {
      deleteMutation.mutate(documentToDelete);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDocumentToDelete(null);
  };

  const handleDownloadDocument = async (documentId: string, filename: string) => {
    try {
      setDownloadingDocId(documentId);
      const blob = await documentService.getDocumentFile(documentId);
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary anchor element and trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading document:', error);
    } finally {
      setDownloadingDocId(null);
    }
  };

  return (
    <Box>
      <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4">
            Documents
          </Typography>
          <Tooltip title="Upload a new document">
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={() => navigate('/documents/upload')}
            >
              Upload Document
            </Button>
          </Tooltip>
        </Box>
        <Typography variant="body1" color="text.secondary">
          View and manage your uploaded documents
        </Typography>
      </Paper>

      <Paper sx={{ p: 3, mb: 4 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange} 
            aria-label="document source tabs"
            sx={{ mb: 2 }}
          >
            <Tab 
              icon={<DescriptionIcon sx={{ mr: 1 }} />} 
              iconPosition="start" 
              label="My Documents" 
              {...a11yProps(0)} 
            />
            <Tab 
              icon={<CloudQueueIcon sx={{ mr: 1 }} />} 
              iconPosition="start" 
              label="Google Drive" 
              {...a11yProps(1)} 
            />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel id="document-type-label">Document Type</InputLabel>
                <Select
                  labelId="document-type-label"
                  value={documentType}
                  label="Document Type"
                  onChange={handleDocumentTypeChange}
                >
                  <MenuItem value="">All Types</MenuItem>
                  <MenuItem value="pdf">PDF</MenuItem>
                  <MenuItem value="docx">DOCX</MenuItem>
                  <MenuItem value="pptx">PPTX</MenuItem>
                  <MenuItem value="xlsx">XLSX</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel id="page-size-label">Items Per Page</InputLabel>
                <Select
                  labelId="page-size-label"
                  value={pageSize}
                  label="Items Per Page"
                  onChange={handlePageSizeChange}
                >
                  <MenuItem value={5}>5</MenuItem>
                  <MenuItem value={10}>10</MenuItem>
                  <MenuItem value={25}>25</MenuItem>
                  <MenuItem value={50}>50</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          {isLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Error loading documents: {(error as Error).message}
            </Alert>
          )}

          {data && data.documents.length === 0 && (
            <Paper
              elevation={0}
              sx={{
                p: 4,
                mb: 3,
                borderRadius: 2,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'var(--ey-dark-gray)',
                border: '1px solid var(--ey-medium-gray)',
                color: 'var(--ey-white)',
              }}
            >
              <Box
                sx={{
                  width: 70,
                  height: 70,
                  borderRadius: '50%',
                  backgroundColor: 'rgba(255, 230, 0, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mb: 2,
                  border: '2px solid var(--ey-yellow)',
                }}
              >
                <InsertDriveFileIcon 
                  sx={{ 
                    fontSize: 34, 
                    color: 'var(--ey-yellow)'
                  }} 
                />
              </Box>
              <Typography variant="h6" fontWeight="medium" sx={{ mb: 1, color: 'var(--ey-white)' }}>
                No documents found
              </Typography>
              <Typography variant="body1" sx={{ mb: 3, color: 'var(--ey-light-gray)', textAlign: 'center' }}>
                Upload a document to get started with analysis
              </Typography>
              <Tooltip title="Upload a document to get started">
                <Button 
                  variant="contained"
                  onClick={() => navigate('/documents/upload')}
                  sx={{ 
                    backgroundColor: 'var(--ey-yellow)',
                    color: 'var(--ey-dark-gray)',
                    '&:hover': {
                      backgroundColor: 'var(--ey-yellow-hover)',
                    }
                  }}
                  startIcon={<CloudUploadIcon />}
                >
                  Upload Document
                </Button>
              </Tooltip>
            </Paper>
          )}

          {data && data.documents.length > 0 && (
            <>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Filename</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Chunks</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell>Tags</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.documents.map((document) => (
                      <TableRow key={document.document_id}>
                        <TableCell>{document.filename}</TableCell>
                        <TableCell>
                          <Chip 
                            label={document.document_type.toUpperCase()} 
                            size="small" 
                            color="primary" 
                            variant="outlined" 
                          />
                        </TableCell>
                        <TableCell>{document.total_chunks}</TableCell>
                        <TableCell>
                          {new Date(document.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          {document.tags.map((tag: string) => (
                            <Chip 
                              key={tag} 
                              label={tag} 
                              size="small" 
                              sx={{ mr: 0.5, mb: 0.5 }} 
                            />
                          ))}
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="View details">
                            <IconButton 
                              color="primary" 
                              onClick={() => navigate(`/documents/${document.document_id}`)}
                            >
                              <VisibilityIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Download">
                            <IconButton 
                              color="primary"
                              onClick={() => handleDownloadDocument(document.document_id, document.filename)}
                              disabled={downloadingDocId === document.document_id}
                            >
                              {downloadingDocId === document.document_id ? (
                                <CircularProgress size={24} />
                              ) : (
                                <DownloadIcon />
                              )}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete">
                            <IconButton 
                              color="error" 
                              onClick={() => handleDeleteClick(document.document_id)}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                <Pagination 
                  count={data.pagination.total_pages} 
                  page={page} 
                  onChange={handlePageChange} 
                  color="primary" 
                />
              </Box>
            </>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <DriveIntegration />
        </TabPanel>
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this document? This action cannot be undone.
            <br /><br />
            <strong>The document will be permanently removed from:</strong>
            <ul>
              <li>Search results</li>
              <li>Document storage</li>
              <li>File uploads</li>
            </ul>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Tooltip title="Cancel deletion">
            <Button onClick={handleDeleteCancel}>Cancel</Button>
          </Tooltip>
          <Tooltip title={deleteMutation.isPending ? "Delete in progress" : "Permanently delete this document"}>
            <Button 
              onClick={handleDeleteConfirm} 
              color="error" 
              autoFocus
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 
                <><CircularProgress size={16} sx={{ mr: 1 }} /> Deleting...</> : 
                'Delete'
              }
            </Button>
          </Tooltip>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DocumentList; 