import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Button,
  Divider,
  Tooltip,
  IconButton,
  Fade,
  Snackbar,
  Chip
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import DownloadIcon from '@mui/icons-material/Download';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import FindInPageIcon from '@mui/icons-material/FindInPage';
import { documentService } from '../../services/documentService';

// Import PDF.js
// @ts-ignore
import * as pdfjsLib from 'pdfjs-dist';

// Set the worker source
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';

// Simplified interface without bounding box
interface DocumentChunk {
  chunk_id: string;
  text: string;
  metadata: {
    page_number?: number;
    [key: string]: any;
  };
}

// Define document type configurations
interface DocumentTypeConfig {
  supportsPageNavigation: boolean;
  description: string;
}

const DocumentViewer: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const documentContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Get chunk_id and page number from location state
  const chunkId = location.state?.chunkId;
  const initialPageNumber = location.state?.pageNumber || 1;
  
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(initialPageNumber);
  const [scale, setScale] = useState<number>(1.2);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [snackbarOpen, setSnackbarOpen] = useState<boolean>(false);
  const [snackbarMessage, setSnackbarMessage] = useState<string>('');
  const [useFallbackViewer, setUseFallbackViewer] = useState<boolean>(false);
  const [pdfDocument, setPdfDocument] = useState<any | null>(null);
  const [isLoadingPage, setIsLoadingPage] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  
  // Define document type configurations
  const documentTypeConfig: Record<string, DocumentTypeConfig> = {
    pdf: {
      supportsPageNavigation: true,
      description: 'PDF documents support page navigation.'
    },
    docx: {
      supportsPageNavigation: false,
      description: 'Word documents are displayed using Microsoft Office Online.'
    },
    doc: {
      supportsPageNavigation: false,
      description: 'Word documents are displayed using Microsoft Office Online.'
    },
    pptx: {
      supportsPageNavigation: false,
      description: 'PowerPoint documents are displayed using Microsoft Office Online.'
    },
    ppt: {
      supportsPageNavigation: false,
      description: 'PowerPoint documents are displayed using Microsoft Office Online.'
    },
    xlsx: {
      supportsPageNavigation: false,
      description: 'Excel documents are displayed using Microsoft Office Online.'
    },
    xls: {
      supportsPageNavigation: false,
      description: 'Excel documents are displayed using Microsoft Office Online.'
    },
    default: {
      supportsPageNavigation: false,
      description: 'This document type does not support page navigation.'
    }
  };
  
  // Fetch document details
  const { data: document, isLoading, error } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentService.getDocumentDetails(documentId!, true),
    enabled: !!documentId
  });
  
  // Set fallback viewer by default for PDFs
  useEffect(() => {
    if (document && document.document_type.toLowerCase() === 'pdf') {
      setUseFallbackViewer(true);
    }
  }, [document]);
  
  // Get document URL
  const getDocumentUrl = () => {
    if (!document) return '';
    
    // Add a timestamp to prevent caching issues
    const timestamp = new Date().getTime();
    
    try {
      // Use the regular document URL
      let url = documentService.getDocumentFileUrl(documentId!);
      
      // Add cache-busting parameter
      url += `?_t=${timestamp}`;
      
      // Add page number if available
      if (chunk?.metadata.page_number) {
        url += `&page=${chunk.metadata.page_number}`;
      } else if (currentPage > 1) {
        url += `&page=${currentPage}`;
      }
      
      console.log('Document URL:', url);
      return url;
    } catch (error) {
      console.error('Error generating document URL:', error);
      // Fallback to direct API URL if there's an error
      let url = `/api/documents/${documentId}/file?_t=${timestamp}`;
      
      // Add page number if available
      if (chunk?.metadata.page_number) {
        url += `&page=${chunk.metadata.page_number}`;
      } else if (currentPage > 1) {
        url += `&page=${currentPage}`;
      }
      
      return url;
    }
  };
  
  // Find the chunk in the document
  const findChunk = () => {
    if (!document || !document.chunks || !chunkId) return null;
    
    return document.chunks.find((chunk: DocumentChunk) => chunk.chunk_id === chunkId);
  };
  
  const chunk = findChunk();
  
  // Handle document download
  const handleDownloadDocument = async () => {
    if (!document) return;
    
    try {
      setIsDownloading(true);
      
      const blob = await documentService.getDocumentFile(documentId!);
      setSnackbarMessage('Downloading document...');
      setSnackbarOpen(true);
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary anchor element and trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = document.filename;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading document:', error);
      setSnackbarMessage('Error downloading document');
      setSnackbarOpen(true);
    } finally {
      setIsDownloading(false);
    }
  };
  
  // Handle zoom in
  const handleZoomIn = () => {
    setScale(prevScale => {
      const newScale = Math.min(prevScale + 0.2, 3);
      renderPdfPage(currentPage, newScale);
      return newScale;
    });
  };
  
  // Handle zoom out
  const handleZoomOut = () => {
    setScale(prevScale => {
      const newScale = Math.max(prevScale - 0.2, 0.6);
      renderPdfPage(currentPage, newScale);
      return newScale;
    });
  };
  
  // Handle fullscreen toggle
  const handleFullscreenToggle = () => {
    setIsFullscreen(!isFullscreen);
    // Re-render the page after toggling fullscreen
    setTimeout(() => {
      renderPdfPage(currentPage, scale);
    }, 100);
  };
  
  // Handle page change
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= (numPages || 1)) {
      setCurrentPage(newPage);
      renderPdfPage(newPage, scale);
    }
  };
  
  // Load PDF document
  const loadPdfDocument = async () => {
    if (!document || document.document_type.toLowerCase() !== 'pdf' || useFallbackViewer) return;
    
    try {
      setLoadError(null);
      const url = getDocumentUrl();
      
      // Load the PDF document
      const loadingTask = pdfjsLib.getDocument(url);
      
      loadingTask.promise.then(
        (pdf: any) => {
          setPdfDocument(pdf);
          setNumPages(pdf.numPages);
          
          // If we have a chunk with page number, navigate to that page
          if (chunk?.metadata.page_number) {
            const pageNum = chunk.metadata.page_number;
            setCurrentPage(pageNum);
            renderPdfPage(pageNum, scale);
            setSnackbarMessage(`Navigated to page ${pageNum}`);
            setSnackbarOpen(true);
          } else {
            renderPdfPage(currentPage, scale);
          }
        },
        (reason: any) => {
          console.error('Error loading PDF:', reason);
          setLoadError(`Failed to load PDF: ${reason.message || 'Unknown error'}`);
          setUseFallbackViewer(true);
        }
      );
    } catch (error) {
      console.error('Error in PDF loading process:', error);
      setLoadError(`Error loading PDF: ${(error as Error).message}`);
      setUseFallbackViewer(true);
    }
  };
  
  // Render PDF page
  const renderPdfPage = async (pageNumber: number, pageScale: number) => {
    if (!pdfDocument || !canvasRef.current) return;
    
    try {
      setIsLoadingPage(true);
      
      // Get the page
      const page = await pdfDocument.getPage(pageNumber);
      
      // Get the canvas and context
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      if (!context) {
        console.error('Could not get canvas context');
        return;
      }
      
      // Calculate viewport with scale
      const viewport = page.getViewport({ scale: pageScale });
      
      // Support HiDPI-screens
      const outputScale = window.devicePixelRatio || 1;
      
      // Set canvas dimensions
      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = Math.floor(viewport.width) + "px";
      canvas.style.height = Math.floor(viewport.height) + "px";
      
      // Create transform for HiDPI screens
      const transform = outputScale !== 1
        ? [outputScale, 0, 0, outputScale, 0, 0]
        : undefined;
      
      // Render the page
      const renderContext = {
        canvasContext: context,
        transform: transform,
        viewport: viewport
      };
      
      await page.render(renderContext).promise;
      setIsLoadingPage(false);
    } catch (error) {
      console.error('Error rendering PDF page:', error);
      setIsLoadingPage(false);
      setLoadError(`Error rendering page ${pageNumber}: ${(error as Error).message}`);
    }
  };
  
  // Set initial page number based on chunk
  useEffect(() => {
    if (chunk?.metadata.page_number) {
      const pageNum = chunk.metadata.page_number;
      setCurrentPage(pageNum);
      
      // If we're using the PDF.js viewer, navigate to the page
      if (pdfDocument && !useFallbackViewer) {
        renderPdfPage(pageNum, scale);
        setSnackbarMessage(`Navigated to page ${pageNum}`);
        setSnackbarOpen(true);
      }
    }
  }, [chunk, pdfDocument, useFallbackViewer]);
  
  // Load PDF when document is loaded
  useEffect(() => {
    if (document && document.document_type.toLowerCase() === 'pdf' && !useFallbackViewer) {
      loadPdfDocument();
    }
  }, [document, useFallbackViewer]);
  
  // Clean up PDF document when component unmounts
  useEffect(() => {
    return () => {
      if (pdfDocument) {
        pdfDocument.destroy();
      }
    };
  }, [pdfDocument]);
  
  // Render document based on type
  const renderDocument = () => {
    if (!document) return null;
    
    const docType = document.document_type.toLowerCase();
    const config = documentTypeConfig[docType] || documentTypeConfig.default;
    
    // Get the target page number from the chunk or current page
    const targetPage = chunk?.metadata.page_number || currentPage;
    
    switch (docType) {
      case 'pdf':
        return (
          <Box sx={{ position: 'relative', width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', mb: 2 }}>
              <Alert severity="info" sx={{ flex: 1 }}>
                {chunk?.metadata.page_number ? `Viewing page ${chunk.metadata.page_number}` : 'Using direct file viewer'}
              </Alert>
              <Tooltip title="Download document">
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownloadDocument}
                  disabled={isDownloading}
                  sx={{ ml: 2 }}
                >
                  {isDownloading ? 'Downloading...' : 'Download'}
                </Button>
              </Tooltip>
            </Box>
            <Box id="document-container" sx={{ width: '100%', height: '700px', border: '1px solid #ccc', position: 'relative' }}>
              <iframe 
                src={`${getDocumentUrl()}#page=${targetPage}`}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="PDF Viewer"
                onLoad={() => {
                  setSnackbarMessage(`Navigated to page ${targetPage}`);
                  setSnackbarOpen(true);
                }}
                onError={(e) => {
                  console.error('Error loading document directly');
                  setSnackbarMessage('Error loading document directly. Trying fallback viewer...');
                  setSnackbarOpen(true);
                  
                  // If direct viewing fails, try Google Docs viewer as fallback
                  const iframe = document.createElement('iframe');
                  iframe.src = `https://docs.google.com/viewer?url=${encodeURIComponent(getDocumentUrl())}&embedded=true#page=${targetPage}`;
                  iframe.style.width = '100%';
                  iframe.style.height = '100%';
                  iframe.style.border = 'none';
                  
                  const container = document.getElementById('document-container');
                  if (container) {
                    container.innerHTML = '';
                    container.appendChild(iframe);
                  }
                }}
              />
              <Box 
                sx={{ 
                  position: 'absolute', 
                  top: 0, 
                  left: 0, 
                  right: 0, 
                  bottom: 0, 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center',
                  backgroundColor: 'rgba(255, 255, 255, 0.7)',
                  zIndex: -1
                }}
              >
                <CircularProgress />
              </Box>
            </Box>
            <Box sx={{ mt: 2, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                If the document doesn't load properly, you can download it and view it in your preferred PDF viewer.
              </Typography>
              <Tooltip title="Open document in a new tab">
                <Button
                  variant="text"
                  color="primary"
                  href={getDocumentUrl()}
                  target="_blank"
                  sx={{ mt: 1 }}
                >
                  Open document directly
                </Button>
              </Tooltip>
            </Box>
          </Box>
        );
      
      case 'docx':
      case 'doc':
      case 'word':
        // For Word documents, try direct viewing first, then fallback to Office Online
        return (
          <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', mb: 2 }}>
              <Alert severity="info" sx={{ flex: 1 }}>
                {config.description}
              </Alert>
              <Tooltip title="Download document">
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownloadDocument}
                  disabled={isDownloading}
                  sx={{ ml: 2 }}
                >
                  {isDownloading ? 'Downloading...' : 'Download'}
                </Button>
              </Tooltip>
            </Box>
            <Box id="document-container" sx={{ width: '100%', height: '700px', border: '1px solid #ccc' }}>
              <iframe 
                src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(getDocumentUrl())}`}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="Word Document Viewer"
              />
            </Box>
            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Tooltip title="Open document in a new tab">
                <Button
                  variant="text"
                  color="primary"
                  href={getDocumentUrl()}
                  target="_blank"
                >
                  Open document directly
                </Button>
              </Tooltip>
            </Box>
          </Box>
        );
      
      case 'pptx':
      case 'ppt':
      case 'powerpoint':
        // For PowerPoint documents, try direct viewing first, then fallback to Office Online
        return (
          <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', mb: 2 }}>
              <Alert severity="info" sx={{ flex: 1 }}>
                {config.description}
              </Alert>
              <Tooltip title="Download document">
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownloadDocument}
                  disabled={isDownloading}
                  sx={{ ml: 2 }}
                >
                  {isDownloading ? 'Downloading...' : 'Download'}
                </Button>
              </Tooltip>
            </Box>
            <Box id="document-container" sx={{ width: '100%', height: '700px', border: '1px solid #ccc' }}>
              <iframe 
                src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(getDocumentUrl())}`}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="PowerPoint Document Viewer"
              />
            </Box>
            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Tooltip title="Open document in a new tab">
                <Button
                  variant="text"
                  color="primary"
                  href={getDocumentUrl()}
                  target="_blank"
                >
                  Open document directly
                </Button>
              </Tooltip>
            </Box>
          </Box>
        );
      
      case 'xlsx':
      case 'xls':
      case 'excel':
        // For Excel documents, try direct viewing first, then fallback to Office Online
        return (
          <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', mb: 2 }}>
              <Alert severity="info" sx={{ flex: 1 }}>
                {config.description}
              </Alert>
              <Tooltip title="Download document">
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownloadDocument}
                  disabled={isDownloading}
                  sx={{ ml: 2 }}
                >
                  {isDownloading ? 'Downloading...' : 'Download'}
                </Button>
              </Tooltip>
            </Box>
            <Box id="document-container" sx={{ width: '100%', height: '700px', border: '1px solid #ccc' }}>
              <iframe 
                src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(getDocumentUrl())}`}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="Excel Document Viewer"
              />
            </Box>
            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Tooltip title="Open document in a new tab">
                <Button
                  variant="text"
                  color="primary"
                  href={getDocumentUrl()}
                  target="_blank"
                >
                  Open document directly
                </Button>
              </Tooltip>
            </Box>
          </Box>
        );
      
      default:
        return (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              Preview is currently not available for {document.document_type} documents. You can download the file to view it.
            </Alert>
            <Tooltip title="Download document">
              <Button
                variant="contained"
                color="primary"
                startIcon={<DownloadIcon />}
                onClick={handleDownloadDocument}
                disabled={isDownloading}
              >
                {isDownloading ? 'Downloading...' : 'Download Document'}
              </Button>
            </Tooltip>
            <Box sx={{ mt: 2 }}>
              <Tooltip title="Open document in a new tab">
                <Button
                  variant="outlined"
                  color="primary"
                  href={getDocumentUrl()}
                  target="_blank"
                >
                  Open document directly
                </Button>
              </Tooltip>
            </Box>
          </Box>
        );
    }
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
        <Tooltip title="Return to previous page">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate(-1)}
            sx={{ mb: 2 }}
          >
            Back
          </Button>
        </Tooltip>
        <Alert severity="error">
          Error loading document: {(error as Error).message}
        </Alert>
      </Box>
    );
  }
  
  if (!document) {
    return (
      <Box>
        <Tooltip title="Return to previous page">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate(-1)}
            sx={{ mb: 2 }}
          >
            Back
          </Button>
        </Tooltip>
        <Alert severity="error">
          Document not found
        </Alert>
      </Box>
    );
  }
  
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 140px)' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Tooltip title="Return to previous page">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate(-1)}
          >
            Back
          </Button>
        </Tooltip>
        <Box>
          <Typography variant="h6">
            {document.filename}
          </Typography>
        </Box>
        <Box>
          <Tooltip title="Download document">
            <IconButton 
              onClick={handleDownloadDocument}
              disabled={isDownloading}
              sx={{ mr: 1 }}
            >
              {isDownloading ? <CircularProgress size={24} /> : <DownloadIcon />}
            </IconButton>
          </Tooltip>
          {document.document_type.toLowerCase() === 'pdf' && !useFallbackViewer && (
            <>
              <Tooltip title="Zoom out">
                <IconButton onClick={handleZoomOut}>
                  <ZoomOutIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Zoom in">
                <IconButton onClick={handleZoomIn}>
                  <ZoomInIcon />
                </IconButton>
              </Tooltip>
            </>
          )}
          <Tooltip title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}>
            <IconButton onClick={handleFullscreenToggle}>
              {isFullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      
      {chunk && (
        <Paper 
          elevation={3} 
          sx={{ 
            p: 2, 
            mb: 2, 
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'primary.main',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, height: '4px', bgcolor: 'primary.main' }} />
          
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <FindInPageIcon sx={{ mr: 1, color: 'primary.main' }} />
            Text from Document
            {chunk.metadata.page_number && (
              <Chip 
                label={`Page ${chunk.metadata.page_number}`} 
                size="small" 
                color="primary" 
                sx={{ ml: 1 }}
              />
            )}
          </Typography>
          
          <Typography variant="body2" sx={{ 
            fontFamily: 'monospace', 
            whiteSpace: 'pre-wrap', 
            backgroundColor: 'rgba(255, 230, 0, 0.1)', 
            p: 2, 
            borderRadius: 1,
            border: '1px solid rgba(255, 230, 0, 0.3)',
            maxHeight: '150px',
            overflow: 'auto'
          }}>
            {chunk.text.replace(/<em>/g, '<em style="background-color: rgba(255, 230, 0, 0.3); font-style: normal; padding: 0 2px;">')}
          </Typography>
          
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              Source: {document.filename}
              {chunk.metadata.page_number && ` - Page ${chunk.metadata.page_number}`}
            </Typography>
            
            {document.document_type.toLowerCase() === 'pdf' && chunk.metadata.page_number && !useFallbackViewer && (
              <Tooltip title={`Jump to page ${chunk.metadata.page_number}`}>
                <Button 
                  size="small" 
                  variant="outlined" 
                  color="primary"
                  onClick={() => {
                    setCurrentPage(chunk.metadata.page_number);
                    renderPdfPage(chunk.metadata.page_number, scale);
                  }}
                >
                  Go to Page {chunk.metadata.page_number}
                </Button>
              </Tooltip>
            )}
          </Box>
        </Paper>
      )}
      
      <Paper 
        ref={documentContainerRef}
        sx={{ 
          p: 2, 
          flexGrow: 1, 
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          ...(isFullscreen ? {
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 1300,
            borderRadius: 0,
          } : {})
        }}
      >
        {renderDocument()}
      </Paper>
      
      {document.document_type.toLowerCase() === 'pdf' && numPages && numPages > 1 && !useFallbackViewer && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 2 }}>
          <Tooltip title="Go to previous page">
            <span>
              <Button 
                disabled={currentPage <= 1}
                onClick={() => handlePageChange(currentPage - 1)}
                startIcon={<NavigateBeforeIcon />}
                variant="outlined"
                sx={{ mr: 2 }}
              >
                Previous
              </Button>
            </span>
          </Tooltip>
          <Typography variant="body2">
            Page {currentPage} of {numPages}
          </Typography>
          <Tooltip title="Go to next page">
            <span>
              <Button 
                disabled={currentPage >= numPages}
                onClick={() => handlePageChange(currentPage + 1)}
                endIcon={<NavigateNextIcon />}
                variant="outlined"
                sx={{ ml: 2 }}
              >
                Next
              </Button>
            </span>
          </Tooltip>
        </Box>
      )}
      
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
};

export default DocumentViewer; 