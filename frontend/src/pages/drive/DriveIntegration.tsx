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
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Divider,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Checkbox,
  Breadcrumbs,
  Link,
  FormControl,
  InputLabel,
  Select,
  OutlinedInput,
  MenuItem,
  InputAdornment,
  Menu,
  IconButton,
  Tooltip
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SearchIcon from '@mui/icons-material/Search';
import SortIcon from '@mui/icons-material/Sort';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import DataUsageIcon from '@mui/icons-material/DataUsage';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import ArticleIcon from '@mui/icons-material/Article';
import TableChartIcon from '@mui/icons-material/TableChart';
import SlideshowIcon from '@mui/icons-material/Slideshow';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import ClearIcon from '@mui/icons-material/Clear';
import { driveService, DriveFile } from '../../services/driveService';
import { DocumentMetadata } from '../../services/documentService';
import { useAuth } from '../../context/AuthContext';
import { useAppState } from '../../context/StateContext';

const DriveIntegration: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { state, updateState } = useAppState();
  const [currentFolderId, setCurrentFolderId] = useState<string | undefined>(
    state.drive?.currentFolderId
  );
  const [folderPath, setFolderPath] = useState<Array<{ id: string, name: string }>>(
    state.drive?.folderPath || []
  );
  const [selectedFiles, setSelectedFiles] = useState<DriveFile[]>([]);
  const [isMetadataDialogOpen, setIsMetadataDialogOpen] = useState(false);
  const [createdBy, setCreatedBy] = useState(user?.email || '');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [processingResults, setProcessingResults] = useState<Record<string, boolean>>({});
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFileTypes, setSelectedFileTypes] = useState<string[]>([]);
  const [sortAnchorEl, setSortAnchorEl] = useState<null | HTMLElement>(null);
  const [sortBy, setSortBy] = useState<string>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Supported file types with friendly names
  const fileTypeOptions = [
    { value: 'pdf', label: 'PDF Documents', mimeType: 'application/pdf' },
    { value: 'docx', label: 'Word Documents', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
    { value: 'doc', label: 'Word Documents (Legacy)', mimeType: 'application/msword' },
    { value: 'pptx', label: 'PowerPoint Presentations', mimeType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' },
    { value: 'ppt', label: 'PowerPoint (Legacy)', mimeType: 'application/vnd.ms-powerpoint' },
    { value: 'xlsx', label: 'Excel Spreadsheets', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
    { value: 'xls', label: 'Excel (Legacy)', mimeType: 'application/vnd.ms-excel' },
    { value: 'csv', label: 'CSV Files', mimeType: 'text/csv' },
    { value: 'gdoc', label: 'Google Docs', mimeType: 'application/vnd.google-apps.document' },
    { value: 'gsheet', label: 'Google Sheets', mimeType: 'application/vnd.google-apps.spreadsheet' },
    { value: 'gslides', label: 'Google Slides', mimeType: 'application/vnd.google-apps.presentation' }
  ];

  // Get auth URL
  const getAuthUrlQuery = useQuery({
    queryKey: ['driveAuthUrl'],
    queryFn: () => driveService.getAuthUrl(),
    enabled: !isAuthenticated
  });

  // Set auth URL when available
  useEffect(() => {
    if (getAuthUrlQuery.data) {
      // Use the auth URL directly from the backend
      setAuthUrl(getAuthUrlQuery.data.toString());
    }
  }, [getAuthUrlQuery.data]);

  // Authenticate with Google Drive - we'll still need this for polling status 
  // but no longer for handling the initial redirect
  const authenticateMutation = useMutation({
    mutationFn: (code: string) => driveService.authenticate(code),
    onSuccess: () => {
      setIsAuthenticated(true);
      queryClient.invalidateQueries({ queryKey: ['driveFiles'] });
    }
  });

  // Check authentication status when component mounts
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const isValid = await driveService.checkDriveCredentials();
        setIsAuthenticated(isValid);
      } catch (error) {
        console.error('Error checking authentication status:', error);
        setIsAuthenticated(false);
      }
    };
    
    checkAuthStatus();
  }, []);

  // Check if we're embedded in the DocumentList component
  useEffect(() => {
    // If we're directly accessing /drive, redirect to /documents?tab=1
    if (location.pathname === '/drive') {
      navigate('/documents?tab=1');
    }
  }, [location, navigate]);

  // List files in Google Drive
  const { data: files, isLoading, error } = useQuery<DriveFile[]>({
    queryKey: ['driveFiles', currentFolderId],
    queryFn: () => driveService.listFiles(currentFolderId, selectedFileTypes.map(type => type.split('/')[1])),
    enabled: isAuthenticated
  });

  // Handle authentication errors
  useEffect(() => {
    if (error) {
      // If we get an error, we might need to re-authenticate
      setIsAuthenticated(false);
    }
  }, [error]);

  // Persist state changes to the StateContext
  useEffect(() => {
    updateState({
      drive: {
        currentFolderId,
        folderPath,
        selectedFileTypes,
        sortBy,
        sortDirection
      }
    });
  }, [currentFolderId, folderPath, selectedFileTypes, sortBy, sortDirection, updateState]);

  // Process selected files
  const processFilesMutation = useMutation({
    mutationFn: async () => {
      // Format metadata properly to match the expected structure
      const metadata: DocumentMetadata = {
        created_by: createdBy || user?.email || undefined,
        user_id: user?.id,
        tags: tags.length > 0 ? tags : undefined,
        // Add additional metadata to track the source
        additional_metadata: {
          source: 'google_drive',
          drive_file_ids: selectedFiles.map(file => file.id),
          import_date: new Date().toISOString()
        }
      };
      
      return driveService.batchProcessFiles(
        selectedFiles.map(file => file.id),
        metadata
      );
    },
    onSuccess: () => {
      // Mark files as processed
      const newResults: Record<string, boolean> = {};
      selectedFiles.forEach((file) => {
        newResults[file.id] = true;
      });
      setProcessingResults(newResults);
      
      // Clear selection
      setSelectedFiles([]);
      
      // Close dialog
      setIsMetadataDialogOpen(false);
      
      // Refresh both drive files and documents lists
      queryClient.invalidateQueries({ queryKey: ['driveFiles'] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  });

  const handleFolderClick = (folder: DriveFile) => {
    setCurrentFolderId(folder.id);
    setFolderPath([...folderPath, { id: folder.id, name: folder.name }]);
    setSelectedFiles([]);
  };

  const handleBackClick = () => {
    if (folderPath.length > 0) {
      const newPath = [...folderPath];
      newPath.pop();
      setFolderPath(newPath);
      setCurrentFolderId(newPath.length > 0 ? newPath[newPath.length - 1].id : undefined);
      setSelectedFiles([]);
    }
  };

  const handleFileSelection = (file: DriveFile) => {
    if (selectedFiles.some(f => f.id === file.id)) {
      setSelectedFiles(selectedFiles.filter(f => f.id !== file.id));
    } else {
      setSelectedFiles([...selectedFiles, file]);
    }
  };

  const handleProcessFiles = () => {
    if (selectedFiles.length > 0) {
      setIsMetadataDialogOpen(true);
    }
  };

  const handleAddTag = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && tagInput.trim()) {
      if (!tags.includes(tagInput.trim())) {
        setTags(prev => [...prev, tagInput.trim()]);
      }
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(prev => prev.filter(tag => tag !== tagToRemove));
  };

  const handleAuthenticate = () => {
    if (authUrl) {
      // Save the current page to return to after authentication
      localStorage.setItem('returnToPath', location.pathname);
      
      // Use redirect flow with our dedicated callback route
      window.location.href = authUrl;
    } else {
      // If no auth URL is available yet, get it first
      getAuthUrlQuery.refetch().then(result => {
        if (result.data) {
          window.location.href = result.data.toString();
        }
      });
    }
  };

  const isFileProcessed = (file: DriveFile) => {
    return processingResults[file.id] === true;
  };

  // Get an appropriate icon for the file type
  const getFileIcon = (mimeType: string) => {
    // PDF
    if (mimeType === 'application/pdf') {
      return <PictureAsPdfIcon sx={{ color: '#ffe600' }} fontSize="medium" />;
    }
    
    // Google Docs
    if (mimeType === 'application/vnd.google-apps.document') {
      return <ArticleIcon sx={{ color: '#333333' }} fontSize="medium" />;
    }
    
    // Google Sheets
    if (mimeType === 'application/vnd.google-apps.spreadsheet' || 
        mimeType.includes('spreadsheet') || 
        mimeType.includes('excel')) {
      return <TableChartIcon sx={{ color: '#999999' }} fontSize="medium" />;
    }
    
    // Google Slides
    if (mimeType === 'application/vnd.google-apps.presentation') {
      return <SlideshowIcon sx={{ color: '#ffe600' }} fontSize="medium" />;
    }
    
    // Folder
    if (mimeType === 'application/vnd.google-apps.folder') {
      return <FolderIcon sx={{ color: '#ffe600' }} fontSize="medium" />;
    }
    
    // Default
    return <DescriptionIcon sx={{ color: '#999999' }} fontSize="medium" />;
  };

  // Helper to get file type label
  const getFileTypeLabel = (mimeType: string) => {
    const fileType = fileTypeOptions.find(opt => opt.mimeType === mimeType);
    if (fileType) return fileType.label;
    
    switch (mimeType) {
      case 'application/vnd.google-apps.folder':
        return 'Folder';
      default:
        return mimeType.split('/').pop()?.toUpperCase() || 'Unknown';
    }
  };

  // Sort options
  const sortOptions = [
    { value: 'name', label: 'Name', icon: <InsertDriveFileIcon /> },
    { value: 'modifiedTime', label: 'Last Modified', icon: <AccessTimeIcon /> },
    { value: 'size', label: 'Size', icon: <DataUsageIcon /> },
    { value: 'fileType', label: 'File Type', icon: <DescriptionIcon /> },
  ];

  // Handle sort menu
  const handleSortClick = (event: React.MouseEvent<HTMLElement>) => {
    setSortAnchorEl(event.currentTarget);
  };

  const handleSortClose = () => {
    setSortAnchorEl(null);
  };

  const handleSortSelect = (value: string) => {
    if (sortBy === value) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(value);
      setSortDirection('asc');
    }
    handleSortClose();
  };

  // Sort files
  const sortFiles = (files: DriveFile[]) => {
    return [...files].sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'modifiedTime':
          comparison = new Date(a.modifiedTime).getTime() - new Date(b.modifiedTime).getTime();
          break;
        case 'size':
          const sizeA = a.size ? parseInt(a.size) : 0;
          const sizeB = b.size ? parseInt(b.size) : 0;
          comparison = sizeA - sizeB;
          break;
        case 'fileType':
          const typeA = a.mimeType.split('/').pop() || '';
          const typeB = b.mimeType.split('/').pop() || '';
          comparison = typeA.localeCompare(typeB);
          break;
      }
      
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  };

  // Filter and sort files
  const filteredAndSortedFiles = React.useMemo(() => {
    if (!files) return [];
    
    // Separate folders and files
    const folders = files.filter(file => file.mimeType === 'application/vnd.google-apps.folder');
    const nonFolders = files.filter(file => file.mimeType !== 'application/vnd.google-apps.folder');
    
    // Only apply search and type filters to non-folder files
    const filteredFiles = nonFolders.filter(file => {
      const matchesSearch = !searchQuery.trim() || 
        file.name.toLowerCase().includes(searchQuery.toLowerCase().trim());
      
      const matchesType = selectedFileTypes.length === 0 || 
        selectedFileTypes.some(type => {
          const fileType = fileTypeOptions.find(opt => opt.value === type);
          return fileType && file.mimeType === fileType.mimeType;
        });
      
      return matchesSearch && matchesType;
    });

    // Only show folders if there's no search, or if they match the search
    const filteredFolders = !searchQuery.trim() 
      ? folders 
      : folders.filter(folder => folder.name.toLowerCase().includes(searchQuery.toLowerCase().trim()));
    
    // Combine folders and filtered files, ensuring folders always come first
    return sortFiles([...filteredFolders, ...filteredFiles]);
  }, [files, searchQuery, selectedFileTypes, sortBy, sortDirection, fileTypeOptions]);

  // Update the search input to handle empty strings better
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  // Update renderFolders and renderFiles to not filter by type again
  const renderFolders = () => {
    if (!filteredAndSortedFiles) return null;
    
    return filteredAndSortedFiles
      .filter(file => file.mimeType === 'application/vnd.google-apps.folder')
      .map((folder) => (
        <React.Fragment key={folder.id}>
          <ListItem disablePadding>
            <ListItemButton 
              onClick={() => handleFolderClick(folder)}
              sx={{
                '&:hover .folder-icon': {
                  display: 'none'
                },
                '&:hover .folder-open-icon': {
                  display: 'block'
                }
              }}
            >
              <ListItemIcon>
                <Box sx={{ position: 'relative' }}>
                  <Box className="folder-icon">
                    <FolderIcon sx={{ color: '#ffe600' }} />
                  </Box>
                  <Box 
                    className="folder-open-icon" 
                    sx={{ 
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      display: 'none'
                    }}
                  >
                    <FolderOpenIcon sx={{ color: '#ffe600' }} />
                  </Box>
                </Box>
              </ListItemIcon>
              <ListItemText 
                primary={folder.name} 
                secondary={`Modified: ${new Date(folder.modifiedTime).toLocaleString()}`} 
              />
            </ListItemButton>
          </ListItem>
          <Divider />
        </React.Fragment>
      ));
  };

  const renderFiles = (files: DriveFile[]) => {
    if (!files) return null;
    
    return files
      .filter(file => file.mimeType !== 'application/vnd.google-apps.folder')
      .map((file) => (
        <React.Fragment key={file.id}>
          <ListItem>
            <ListItemIcon>
              <Checkbox
                edge="start"
                checked={selectedFiles.some(f => f.id === file.id)}
                onChange={() => handleFileSelection(file)}
                disabled={isFileProcessed(file)}
              />
            </ListItemIcon>
            <ListItemIcon>
              {getFileIcon(file.mimeType)}
            </ListItemIcon>
            <ListItemText 
              primary={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {file.name}
                  {isFileProcessed(file) && (
                    <Chip 
                      icon={<CheckCircleIcon />} 
                      label="Processed" 
                      color="success" 
                      size="small" 
                      sx={{ ml: 1 }} 
                    />
                  )}
                </Box>
              } 
              secondary={
                <>
                  <Chip 
                    label={getFileTypeLabel(file.mimeType)}
                    size="small"
                    sx={{ 
                      mr: 1,
                      backgroundColor: 'rgba(204, 204, 204, 0.2)',
                      '& .MuiChip-label': {
                        fontSize: '0.75rem'
                      }
                    }}
                  />
                  {file.size ? `${(parseInt(file.size) / 1024 / 1024).toFixed(2)} MB • ` : ''}
                  Modified: {new Date(file.modifiedTime).toLocaleString()}
                </>
              } 
            />
          </ListItem>
          <Divider />
        </React.Fragment>
      ));
  };

  return (
    <Box>
      <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Google Drive Integration
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Connect to your Google Drive to process documents directly from your cloud storage
        </Typography>
        
        {!isAuthenticated && (
          <Tooltip title="Connect your Google Drive account">
            <Button
              variant="contained"
              color="primary"
              startIcon={<CloudDownloadIcon />}
              onClick={handleAuthenticate}
              disabled={getAuthUrlQuery.isLoading || !authUrl}
            >
              {getAuthUrlQuery.isLoading ? <CircularProgress size={24} /> : 'Connect to Google Drive'}
            </Button>
          </Tooltip>
        )}
      </Paper>

      {authenticateMutation.isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Authentication error: {(authenticateMutation.error as Error).message}
        </Alert>
      )}

      {isAuthenticated && (
        <Paper sx={{ p: 3 }}>
          {/* Search and Filter Controls */}
          <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField
              placeholder="Search files..."
              value={searchQuery}
              onChange={handleSearchChange}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setSearchQuery('');
                }
              }}
              sx={{ flexGrow: 1 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
                endAdornment: searchQuery && (
                  <InputAdornment position="end">
                    <Tooltip title="Clear search">
                      <IconButton
                        aria-label="clear search"
                        onClick={() => setSearchQuery('')}
                        edge="end"
                        size="small"
                      >
                        <ClearIcon />
                      </IconButton>
                    </Tooltip>
                  </InputAdornment>
                )
              }}
            />
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel id="file-type-label">File Types</InputLabel>
              <Select
                labelId="file-type-label"
                multiple
                value={selectedFileTypes}
                onChange={(e) => setSelectedFileTypes(typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value)}
                input={<OutlinedInput label="File Types" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip 
                        key={value} 
                        label={fileTypeOptions.find(opt => opt.value === value)?.label || value}
                        size="small"
                      />
                    ))}
                  </Box>
                )}
              >
                {fileTypeOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    <Checkbox checked={selectedFileTypes.indexOf(option.value) > -1} />
                    <ListItemText primary={option.label} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Tooltip title="Sort by">
              <IconButton 
                onClick={handleSortClick}
                sx={{ 
                  bgcolor: sortAnchorEl ? 'action.selected' : 'transparent',
                  '&:hover': { bgcolor: 'action.hover' }
                }}
              >
                <SortIcon />
              </IconButton>
            </Tooltip>
            <Menu
              anchorEl={sortAnchorEl}
              open={Boolean(sortAnchorEl)}
              onClose={handleSortClose}
            >
              {sortOptions.map((option) => (
                <MenuItem 
                  key={option.value}
                  onClick={() => handleSortSelect(option.value)}
                  selected={sortBy === option.value}
                >
                  <ListItemIcon>
                    {option.icon}
                  </ListItemIcon>
                  <ListItemText primary={option.label} />
                  {sortBy === option.value && (
                    <ListItemIcon sx={{ ml: 1 }}>
                      {sortDirection === 'asc' ? <ArrowUpwardIcon /> : <ArrowDownwardIcon />}
                    </ListItemIcon>
                  )}
                </MenuItem>
              ))}
            </Menu>
          </Box>

          {/* Navigation and Actions */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Tooltip title={folderPath.length === 0 || isLoading ? "No previous folder to return to" : "Return to previous folder"}>
                <span> {/* Wrapper for disabled button */}
                  <Button
                    startIcon={<ArrowBackIcon />}
                    onClick={handleBackClick}
                    disabled={folderPath.length === 0 || isLoading}
                    sx={{ mr: 2 }}
                  >
                    Back
                  </Button>
                </span>
              </Tooltip>
              
              <Breadcrumbs aria-label="folder path">
                <Link
                  component="button"
                  variant="body1"
                  onClick={() => {
                    setCurrentFolderId(undefined);
                    setFolderPath([]);
                  }}
                  sx={{ cursor: 'pointer' }}
                >
                  My Drive
                </Link>
                {folderPath.map((folder, index) => (
                  <Link
                    key={folder.id}
                    component="button"
                    variant="body1"
                    onClick={() => {
                      const newPath = folderPath.slice(0, index + 1);
                      setFolderPath(newPath);
                      setCurrentFolderId(folder.id);
                    }}
                    sx={{ cursor: 'pointer' }}
                  >
                    {folder.name}
                  </Link>
                ))}
              </Breadcrumbs>
            </Box>
            
            <Tooltip title={selectedFiles.length === 0 || processFilesMutation.isPending ? "Select files to process first" : "Process selected files"}>
              <span> {/* Wrapper for disabled button */}
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<CloudUploadIcon />}
                  onClick={handleProcessFiles}
                  disabled={selectedFiles.length === 0 || processFilesMutation.isPending}
                >
                  {processFilesMutation.isPending 
                    ? <CircularProgress size={24} /> 
                    : `Process ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`
                  }
                </Button>
              </span>
            </Tooltip>
          </Box>

          {/* Loading and Error States */}
          {isLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Error loading files: {(error as Error).message}
            </Alert>
          )}

          {filteredAndSortedFiles.length === 0 && !isLoading && (
            <Alert severity="info" sx={{ mb: 3 }}>
              {searchQuery || selectedFileTypes.length > 0 
                ? 'No files match your search criteria.'
                : 'No files found in this location.'}
            </Alert>
          )}

          {/* File List */}
          {filteredAndSortedFiles.length > 0 && (
            <List>
              {/* Folders first */}
              {renderFolders()}
              
              {/* Then files */}
              {renderFiles(filteredAndSortedFiles)}
            </List>
          )}
        </Paper>
      )}

      {/* Metadata Dialog */}
      <Dialog open={isMetadataDialogOpen} onClose={() => setIsMetadataDialogOpen(false)}>
        <DialogTitle>Document Metadata</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Add metadata to the selected documents before processing.
          </DialogContentText>
          
          <TextField
            fullWidth
            label="Created By"
            variant="outlined"
            value={createdBy}
            onChange={(e) => setCreatedBy(e.target.value)}
            margin="normal"
            placeholder="user@example.com"
          />
          
          <TextField
            fullWidth
            label="Add Tags"
            variant="outlined"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleAddTag}
            margin="normal"
            placeholder="Press Enter to add"
            helperText="Add tags to categorize your documents"
          />
          
          <Box sx={{ mt: 2, mb: 3 }}>
            {tags.map((tag) => (
              <Chip
                key={tag}
                label={tag}
                onDelete={() => handleRemoveTag(tag)}
                sx={{ mr: 1, mb: 1 }}
              />
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Tooltip title="Cancel file processing">
            <Button onClick={() => setIsMetadataDialogOpen(false)}>
              Cancel
            </Button>
          </Tooltip>
          <Tooltip title={processFilesMutation.isPending ? "Processing in progress" : "Process selected files with the specified metadata"}>
            <span> {/* Wrapper for disabled button */}
              <Button 
                onClick={() => processFilesMutation.mutate()} 
                color="primary"
                disabled={processFilesMutation.isPending}
              >
                {processFilesMutation.isPending ? <CircularProgress size={24} /> : 'Process Files'}
              </Button>
            </span>
          </Tooltip>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DriveIntegration; 