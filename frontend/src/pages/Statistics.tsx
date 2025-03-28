import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  Grid,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Divider
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import StorageIcon from '@mui/icons-material/Storage';
import ImageIcon from '@mui/icons-material/Image';
import BarChartIcon from '@mui/icons-material/BarChart';
import { documentService, StatisticsResponse } from '../services/documentService';

const Statistics: React.FC = () => {
  const { data, isLoading, error } = useQuery<StatisticsResponse>({
    queryKey: ['statistics'],
    queryFn: () => documentService.getSystemStatistics()
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Error loading statistics: {(error as Error).message}
      </Alert>
    );
  }

  const stats = [
    {
      title: 'Total Documents',
      value: data?.total_documents || 0,
      icon: <DescriptionIcon fontSize="large" color="primary" />,
      description: 'Total number of documents in the system'
    },
    {
      title: 'Total Chunks',
      value: data?.total_chunks || data?.embedding_stats?.total_chunks || 0,
      icon: <StorageIcon fontSize="large" color="primary" />,
      description: 'Total number of document chunks'
    },
    {
      title: 'OCR Chunks',
      value: data?.total_ocr_chunks || 0,
      icon: <ImageIcon fontSize="large" color="primary" />,
      description: 'Number of chunks extracted using OCR'
    },
    {
      title: 'Avg. Chunks per Document',
      value: data?.avg_chunks_per_document 
        ? data.avg_chunks_per_document.toFixed(1) 
        : data?.embedding_stats?.average_chunks_per_document 
          ? data.embedding_stats.average_chunks_per_document.toFixed(1) 
          : '0',
      icon: <BarChartIcon fontSize="large" color="primary" />,
      description: 'Average number of chunks per document'
    }
  ];

  return (
    <Box>
      <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          System Statistics
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Overview of documents and processing statistics
        </Typography>
      </Paper>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {stats.map((stat) => (
          <Grid item xs={12} sm={6} md={3} key={stat.title}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  {stat.icon}
                  <Typography variant="h6" component="div" sx={{ ml: 1 }}>
                    {stat.title}
                  </Typography>
                </Box>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="h3" component="div" sx={{ mb: 1 }}>
                  {stat.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {stat.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {data && (data.documents_by_type || data.document_types) && 
       Object.keys(data.documents_by_type || data.document_types || {}).length > 0 && (
        <>
          <Typography variant="h5" gutterBottom>
            Document Types
          </Typography>
          <Paper sx={{ p: 3 }}>
            <Grid container spacing={2}>
              {Object.entries(data.documents_by_type || data.document_types || {}).map(([type, count]) => (
                <Grid item xs={12} sm={6} md={4} key={type}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 2, borderRadius: 1, bgcolor: 'background.default' }}>
                    <Typography variant="body1">
                      {type.toUpperCase()}
                    </Typography>
                    <Typography variant="body1" fontWeight="bold">
                      {String(count)}
                    </Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </>
      )}
    </Box>
  );
};

export default Statistics; 