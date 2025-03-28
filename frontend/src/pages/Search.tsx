import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Grid,
  Tooltip
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { documentService, QueryRequest } from '../services/documentService';

interface SearchResult {
  chunk_id: string;
  text: string;
  metadata: {
    source_document_name: string;
    source_document_id: string;
    page_number?: number;
    [key: string]: any;
  };
  distance: number;
}

interface SearchResponse {
  results: SearchResult[];
}

const Search: React.FC = () => {
  const [query, setQuery] = useState('');
  const [numResults, setNumResults] = useState(5);
  const [documentType, setDocumentType] = useState<string>('');
  
  const searchMutation = useMutation<SearchResponse, Error, QueryRequest>({
    mutationFn: (queryRequest: QueryRequest) => documentService.queryDocuments(queryRequest),
  });

  const handleSearch = () => {
    if (!query.trim()) return;
    
    const queryRequest: QueryRequest = {
      query: query.trim(),
      top_k: numResults,
    };
    
    if (documentType) {
      queryRequest.filter_document_types = [documentType];
    }
    
    searchMutation.mutate(queryRequest);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleNumResultsChange = (event: SelectChangeEvent<number>) => {
    setNumResults(event.target.value as number);
  };

  const handleDocumentTypeChange = (event: SelectChangeEvent) => {
    setDocumentType(event.target.value);
  };

  return (
    <Box>
      <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Search Documents
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Search across all your documents using semantic search
        </Typography>
        
        <Grid container spacing={2} alignItems="flex-end">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Search Query"
              variant="outlined"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="What were the Q3 revenue numbers?"
            />
          </Grid>
          <Grid item xs={6} md={2}>
            <FormControl fullWidth>
              <InputLabel id="num-results-label">Results</InputLabel>
              <Select
                labelId="num-results-label"
                value={numResults}
                label="Results"
                onChange={handleNumResultsChange}
              >
                <MenuItem value={3}>3</MenuItem>
                <MenuItem value={5}>5</MenuItem>
                <MenuItem value={10}>10</MenuItem>
                <MenuItem value={20}>20</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} md={2}>
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
          <Grid item xs={12} md={2}>
            <Tooltip title={searchMutation.isPending ? "Search in progress" : "Search through your documents"}>
              <Button
                fullWidth
                variant="contained"
                color="primary"
                onClick={handleSearch}
                disabled={searchMutation.isPending || !query.trim()}
                startIcon={searchMutation.isPending ? <CircularProgress size={20} /> : <SearchIcon />}
              >
                Search
              </Button>
            </Tooltip>
          </Grid>
        </Grid>
      </Paper>

      {searchMutation.isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error: {searchMutation.error.message}
        </Alert>
      )}

      {searchMutation.isSuccess && searchMutation.data.results.length === 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          No results found for your query. Try a different search term.
        </Alert>
      )}

      {searchMutation.isSuccess && searchMutation.data.results.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Search Results
          </Typography>
          <List>
            {searchMutation.data.results.map((result: SearchResult, index: number) => (
              <React.Fragment key={result.chunk_id}>
                {index > 0 && <Divider component="li" />}
                <ListItem alignItems="flex-start" sx={{ flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle1" component="div">
                      {result.metadata.source_document_name}
                    </Typography>
                    <Box>
                      {result.metadata.page_number && (
                        <Chip 
                          label={`Page ${result.metadata.page_number}`} 
                          size="small" 
                          sx={{ mr: 1 }} 
                        />
                      )}
                      <Chip 
                        label={`${(1 - result.distance).toFixed(2)} relevance`} 
                        size="small" 
                        color="primary" 
                      />
                    </Box>
                  </Box>
                  <ListItemText
                    primary={
                      <Typography
                        component="div"
                        variant="body1"
                        sx={{
                          backgroundColor: 'background.default',
                          p: 2,
                          borderRadius: 1,
                          fontFamily: 'monospace',
                          whiteSpace: 'pre-wrap',
                        }}
                      >
                        {result.text}
                      </Typography>
                    }
                  />
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
};

export default Search; 