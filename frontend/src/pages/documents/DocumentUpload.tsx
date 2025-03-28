import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { useMutation } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Alert,
  TextField,
  Chip,
  Grid,
  FormControlLabel,
  Switch,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Divider,
  Tooltip
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { documentService, DocumentMetadata } from '../../services/documentService';

const DocumentUpload: React.FC = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [createdBy, setCreatedBy] = useState('');
  const [useParallelProcessing, setUseParallelProcessing] = useState(true);
  const [forceOcr, setForceOcr] = useState(false);
  const [uploadResults, setUploadResults] = useState<Record<string, { success: boolean; message: string }>>({});

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const metadata: DocumentMetadata = {
        created_by: createdBy || undefined,
        tags: tags.length > 0 ? tags : undefined,
        additional_metadata: {
          source: 'local_upload',
          upload_date: new Date().toISOString(),
          file_size: file.size,
          file_type: file.type
        }
      };
      return documentService.uploadDocument(file, metadata, useParallelProcessing, forceOcr);
    },
    onSuccess: (data, file) => {
      setUploadResults(prev => ({
        ...prev,
        [file.name]: { success: true, message: 'Upload successful. Document processing will continue in the background.' }
      }));
    },
    onError: (error, file) => {
      setUploadResults(prev => ({
        ...prev,
        [file.name]: { success: false, message: (error as Error).message }
      }));
    }
  });

  const batchUploadMutation = useMutation({
    mutationFn: async () => {
      const metadata: DocumentMetadata = {
        created_by: createdBy || undefined,
        tags: tags.length > 0 ? tags : undefined,
        additional_metadata: {
          source: 'local_upload',
          upload_date: new Date().toISOString(),
          batch_upload: true,
          file_count: files.length
        }
      };
      return documentService.batchUploadDocuments(files, metadata);
    },
    onSuccess: (data) => {
      const results: Record<string, { success: boolean; message: string }> = {};
      files.forEach(file => {
        results[file.name] = { success: true, message: 'Upload successful. Document processing will continue in the background.' };
      });
      setUploadResults(results);
    },
    onError: (error) => {
      const results: Record<string, { success: boolean; message: string }> = {};
      files.forEach(file => {
        results[file.name] = { success: false, message: (error as Error).message };
      });
      setUploadResults(results);
    }
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/csv': ['.csv']
    }
  });

  const handleRemoveFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    // Also remove from results if exists
    const fileToRemove = files[index];
    if (fileToRemove && uploadResults[fileToRemove.name]) {
      const newResults = { ...uploadResults };
      delete newResults[fileToRemove.name];
      setUploadResults(newResults);
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

  const handleUpload = () => {
    if (files.length === 0) return;
    
    if (files.length === 1) {
      // Single file upload
      uploadMutation.mutate(files[0]);
    } else {
      // Batch upload
      batchUploadMutation.mutate();
    }
  };

  const isUploading = uploadMutation.isPending || batchUploadMutation.isPending;
  const allUploaded = files.length > 0 && files.every(file => uploadResults[file.name]?.success);

  return (
    <Box>
      <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Upload Documents
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload documents to process and analyze with AI
        </Typography>
      </Paper>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 4 }}>
            <Box
              {...getRootProps()}
              sx={{
                border: '2px dashed',
                borderColor: isDragActive ? 'primary.main' : 'divider',
                borderRadius: 1,
                p: 3,
                textAlign: 'center',
                cursor: 'pointer',
                mb: 3,
                backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
              }}
            >
              <input {...getInputProps()} />
              <CloudUploadIcon color="primary" sx={{ fontSize: 48, mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                {isDragActive ? 'Drop files here' : 'Drag and drop files here, or click to select files'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Supported formats: PDF, DOCX, PPTX, XLSX, CSV
              </Typography>
            </Box>

            {files.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Selected Files ({files.length})
                </Typography>
                <List>
                  {files.map((file, index) => (
                    <React.Fragment key={`${file.name}-${index}`}>
                      {index > 0 && <Divider />}
                      <ListItem
                        secondaryAction={
                          <Tooltip title="Remove file from upload list">
                            <IconButton 
                              edge="end" 
                              onClick={() => handleRemoveFile(index)}
                              disabled={isUploading}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        }
                      >
                        <ListItemIcon>
                          {uploadResults[file.name] ? (
                            uploadResults[file.name].success ? (
                              <CheckCircleIcon color="success" />
                            ) : (
                              <ErrorIcon color="error" />
                            )
                          ) : (
                            <InsertDriveFileIcon color="primary" />
                          )}
                        </ListItemIcon>
                        <ListItemText 
                          primary={file.name} 
                          secondary={
                            uploadResults[file.name] 
                              ? uploadResults[file.name].message 
                              : `${(file.size / 1024 / 1024).toFixed(2)} MB`
                          }
                        />
                      </ListItem>
                    </React.Fragment>
                  ))}
                </List>
              </Box>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Tooltip title="Return to documents list without uploading">
                <Button
                  variant="outlined"
                  onClick={() => navigate('/documents')}
                  disabled={isUploading}
                >
                  Cancel
                </Button>
              </Tooltip>
              <Tooltip title={files.length === 0 ? "Add files to upload" : isUploading ? "Upload in progress" : allUploaded ? "All files have been uploaded" : "Upload selected files to the system"}>
                <span> {/* Wrapper needed for disabled buttons */}
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleUpload}
                    disabled={files.length === 0 || isUploading || allUploaded}
                    startIcon={isUploading ? <CircularProgress size={20} /> : undefined}
                  >
                    {isUploading 
                      ? `Uploading (${Object.keys(uploadResults).length}/${files.length})` 
                      : allUploaded 
                        ? 'All Files Uploaded' 
                        : files.length > 1 
                          ? 'Upload All Files' 
                          : 'Upload File'
                    }
                  </Button>
                </span>
              </Tooltip>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 4 }}>
            <Typography variant="h6" gutterBottom>
              Document Metadata
            </Typography>
            
            <TextField
              fullWidth
              label="Created By"
              variant="outlined"
              value={createdBy}
              onChange={(e) => setCreatedBy(e.target.value)}
              margin="normal"
              disabled={isUploading}
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
              disabled={isUploading}
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
                  disabled={isUploading}
                />
              ))}
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              Processing Options
            </Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={useParallelProcessing}
                  onChange={(e) => setUseParallelProcessing(e.target.checked)}
                  disabled={isUploading}
                />
              }
              label="Use Parallel Processing"
            />
            
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
              Parallel processing uses our high API limits to process documents faster.
            </Typography>

            <FormControlLabel
              control={
                <Switch
                  checked={forceOcr}
                  onChange={(e) => setForceOcr(e.target.checked)}
                  disabled={isUploading}
                />
              }
              label="Force OCR Processing"
            />
            
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              OCR processing extracts text from images and scanned documents. May take longer but can improve results for documents with complex layouts or images.
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {allUploaded && (
        <Alert severity="success" sx={{ mt: 2 }}>
          All documents uploaded successfully! Processing will continue in the background even if you leave this page.
          <Tooltip title="Go to documents list">
            <Button 
              color="inherit" 
              size="small" 
              onClick={() => navigate('/documents')}
              sx={{ ml: 2 }}
            >
              View Documents
            </Button>
          </Tooltip>
        </Alert>
      )}
    </Box>
  );
};

export default DocumentUpload; 