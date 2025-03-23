# DocIntel Frontend Development Guide

This guide provides detailed information on how to develop a frontend application for the DocIntel backend system, covering architecture, user flows, implementation details, and best practices.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Key User Flows](#key-user-flows)
- [Core Components](#core-components)
- [State Management](#state-management)
- [API Integration](#api-integration)
- [UI/UX Guidelines](#uiux-guidelines)
- [Implementation Recommendations](#implementation-recommendations)

## Architecture Overview

The DocIntel frontend should be built as a single-page application (SPA) that communicates with the backend via the RESTful API endpoints. The recommended architecture is:

```
frontend/
├── src/                    # Source code
│   ├── components/         # Reusable UI components
│   │   ├── common/         # Shared components (buttons, inputs, etc.)
│   │   ├── document/       # Document-related components
│   │   ├── chat/           # Chat-related components
│   │   └── drive/          # Google Drive integration components
│   ├── pages/              # Page components
│   ├── services/           # API service modules
│   ├── hooks/              # Custom React hooks
│   ├── contexts/           # React context providers
│   ├── utils/              # Utility functions
│   ├── types/              # TypeScript type definitions
│   └── assets/             # Static assets (images, icons, etc.)
├── public/                 # Public assets
├── package.json            # Dependencies and scripts
└── README.md               # Frontend documentation
```

**Recommended Technologies:**
- **Framework**: React with TypeScript
- **Styling**: Tailwind CSS or styled-components
- **State Management**: React Context API with hooks + React Query for API state
- **Routing**: React Router
- **API Communication**: Axios or fetch API with request/response interceptors

## Key User Flows

### 1. Document Management Flow

**Upload and Process Documents:**
1. User navigates to the document upload page
2. User selects a file from their local system or Google Drive
3. User adds optional metadata (tags, additional info)
4. User initiates upload
5. Frontend shows upload and processing progress
6. Once complete, user is redirected to the document details page

**Search and Query Documents:**
1. User enters a natural language query in the search bar
2. Frontend sends the query to the backend
3. Results are displayed with relevant snippets and source information
4. User can click on a result to view the original document with the relevant section highlighted

**Document Management:**
1. User browses the document library
2. User can view document details, download original files, or delete documents
3. System displays document statistics (chunks, types, processing status)

### 2. Chat Conversation Flow

**Creating a New Conversation:**
1. User navigates to the chat interface
2. User creates a new chat session with an optional title
3. Frontend stores the session ID for subsequent messages

**Asking Questions and Receiving Answers:**
1. User types a message in the chat input
2. Frontend sends the message to the backend
3. (Optional) Frontend streams the processing updates in real-time
4. Frontend displays the AI response with citations and references
5. User can click on citations to view the source documents

**Managing Chat Sessions:**
1. User can view a list of their previous chat sessions
2. User can continue a previous conversation
3. User can export or delete chat sessions

### 3. Google Drive Integration Flow

**Connecting to Google Drive:**
1. User navigates to the Drive integration page
2. User clicks on "Connect to Google Drive"
3. OAuth flow redirects to Google for authentication
4. After authentication, user is redirected back to the application

**Importing Documents from Drive:**
1. User browses their Google Drive files
2. User selects files to import
3. User adds optional metadata
4. Frontend shows import progress
5. Imported documents appear in the document library

## Core Components

### Document Module

1. **DocumentUploader**
   - File selection interface
   - Drag-and-drop support
   - Progress indicators
   - Metadata input form

2. **DocumentLibrary**
   - Filterable list of documents
   - Pagination controls
   - Sorting options
   - Bulk operation support

3. **DocumentViewer**
   - Original document display
   - Text highlighting
   - Page navigation (for PDFs)
   - Metadata panel

4. **DocumentSearch**
   - Natural language query input
   - Filter controls
   - Results display with context
   - Relevance indicators

### Chat Module

1. **ChatList**
   - List of chat sessions
   - Filtering and sorting
   - Session metadata display
   - Session management actions

2. **ChatInterface**
   - Message input
   - Message history display
   - Citation markers
   - Streaming indicator

3. **CitationViewer**
   - Source document preview
   - Context display
   - Navigation to full document

### Drive Integration Module

1. **DriveConnector**
   - Authentication button
   - Connection status
   - Account information

2. **DriveFileBrowser**
   - Folder navigation
   - File selection
   - File type filtering
   - Import controls

## State Management

### Local Component State
Use React's `useState` for component-specific state:
- Form inputs
- UI toggles
- Local filtering/sorting

### Global Application State
Use React Context API for shared state:
- User preferences
- Authentication status
- Theme settings
- Global notifications

### API State
Use React Query for all API-related state:
- Data fetching
- Caching
- Loading states
- Error handling

**Example Context Structure:**
```typescript
// User Context
interface UserContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

// UI Context
interface UIContextType {
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  notifications: Notification[];
  addNotification: (notification: Notification) => void;
  dismissNotification: (id: string) => void;
}

// Document Context
interface DocumentContextType {
  selectedDocument: Document | null;
  selectDocument: (document: Document | null) => void;
  documentView: 'list' | 'grid';
  setDocumentView: (view: 'list' | 'grid') => void;
}
```

## API Integration

### API Service Structure

Create a dedicated service module for each API group:

```typescript
// documentService.ts
export const documentService = {
  uploadDocument: async (file: File, metadata?: DocumentMetadata) => {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }
    formData.append('parallel_processing', 'true');
    
    return axios.post('/api/documents/upload', formData);
  },
  
  queryDocuments: async (query: string, options?: QueryOptions) => {
    return axios.post('/api/documents/query', {
      query,
      n_results: options?.nResults || 5,
      filter_criteria: options?.filterCriteria
    });
  },
  
  // More document-related API methods...
};

// chatService.ts
export const chatService = {
  createSession: async (title: string, userId?: string, metadata?: Record<string, any>) => {
    return axios.post('/api/chat/sessions', {
      title,
      user_id: userId,
      metadata
    });
  },
  
  // More chat-related API methods...
};

// driveService.ts
export const driveService = {
  getAuthUrl: async () => {
    return axios.get('/api/drive/auth-url');
  },
  
  // More drive-related API methods...
};
```

### Handling Real-time Streaming

For streaming responses (like chat), implement EventSource handling:

```typescript
export const streamChatResponse = (sessionId: string, queueId: string, onUpdate: (data: any) => void) => {
  const eventSource = new EventSource(`/api/chat/sessions/${sessionId}/realtime-stream/${queueId}`);
  
  eventSource.addEventListener('update', (event) => {
    const data = JSON.parse(event.data);
    onUpdate(data);
  });
  
  eventSource.addEventListener('token', (event) => {
    const data = JSON.parse(event.data);
    onUpdate(data);
  });
  
  eventSource.addEventListener('complete', (event) => {
    const data = JSON.parse(event.data);
    onUpdate(data);
    eventSource.close();
  });
  
  eventSource.addEventListener('error', () => {
    eventSource.close();
  });
  
  return () => eventSource.close(); // Return cleanup function
};
```

### Error Handling

Implement consistent error handling across all API calls:

```typescript
// axiosConfig.ts
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle different error statuses
    if (error.response) {
      const status = error.response.status;
      
      if (status === 401 || status === 403) {
        // Handle authentication errors
      } else if (status === 404) {
        // Handle not found errors
      } else if (status >= 500) {
        // Handle server errors
      }
      
      // Extract error message from API response
      const errorMessage = error.response.data?.detail || 'An error occurred';
      
      // Show error notification
      notificationService.showError(errorMessage);
    } else if (error.request) {
      // Handle network errors
      notificationService.showError('Network error. Please check your connection.');
    } else {
      // Handle other errors
      notificationService.showError('An unexpected error occurred.');
    }
    
    return Promise.reject(error);
  }
);
```

## UI/UX Guidelines

### Layout Structure

**Main Layout Components:**
1. **AppHeader**: Navigation, user info, global search
2. **Sidebar**: Context-specific navigation
3. **MainContent**: Primary content area
4. **ContextPanel**: Secondary information or actions
5. **Footer**: Optional, for additional links or information

### Document Interaction Design

1. **Document Cards**:
   - Show document type icon/thumbnail
   - Display filename and metadata
   - Show chunk count and processing status
   - Provide quick actions (view, download, delete)

2. **Document Details**:
   - Show full metadata
   - Display chunk breakdown
   - Provide edit options for metadata
   - Offer navigation to original file

3. **Search Results**:
   - Highlight matching text
   - Show document source
   - Indicate relevance score
   - Group by document when appropriate

### Chat Interface Design

1. **Message Bubbles**:
   - Clear visual distinction between user and AI messages
   - Timestamp and message status indicators
   - Citations highlighted within text
   - Context menu for message actions

2. **Citation Display**:
   - Inline citation markers
   - Expandable citation details
   - Links to source documents
   - Visual indicator of relevance

3. **Streaming Feedback**:
   - Typing indicator while generating
   - Progress bar for processing stages
   - Real-time token rendering

### Responsive Design Principles

1. Implement mobile-first design approach
2. Use flexbox/grid for adaptive layouts
3. Consider touch interactions for mobile users
4. Adjust information density based on screen size
5. Implement collapsible sections for complex views

### Accessibility Guidelines

1. Use semantic HTML elements
2. Ensure proper keyboard navigation
3. Maintain WCAG 2.1 AA compliance
4. Add appropriate ARIA attributes
5. Ensure sufficient color contrast
6. Provide alternative text for images

## Implementation Recommendations

### Component Implementation Pattern

Use functional components with hooks for a consistent pattern:

```typescript
import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from 'react-query';
import { documentService } from '../services/documentService';

interface DocumentListProps {
  userId?: string;
  documentType?: string;
}

export const DocumentList: React.FC<DocumentListProps> = ({ userId, documentType }) => {
  const [page, setPage] = useState(1);
  const pageSize = 10;
  
  // Fetch documents with React Query
  const { data, isLoading, error, refetch } = useQuery(
    ['documents', userId, documentType, page],
    () => documentService.listDocuments({
      page,
      pageSize,
      documentType,
      userId
    }),
    {
      keepPreviousData: true,
    }
  );
  
  // Delete document mutation
  const deleteMutation = useMutation(
    (documentId: string) => documentService.deleteDocument(documentId),
    {
      onSuccess: () => {
        refetch(); // Refresh the list after deletion
      }
    }
  );
  
  // Handle pagination
  const handleNextPage = () => {
    if (data && page < data.pagination.totalPages) {
      setPage(page + 1);
    }
  };
  
  const handlePrevPage = () => {
    if (page > 1) {
      setPage(page - 1);
    }
  };
  
  // Handle document deletion
  const handleDelete = (documentId: string) => {
    // Show confirmation
    if (confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate(documentId);
    }
  };
  
  return (
    <div className="document-list">
      {isLoading ? (
        <div className="loading-spinner">Loading documents...</div>
      ) : error ? (
        <div className="error-message">Error loading documents</div>
      ) : data?.documents.length === 0 ? (
        <div className="empty-state">No documents found</div>
      ) : (
        <>
          <div className="document-grid">
            {data?.documents.map(document => (
              <DocumentCard 
                key={document.document_id}
                document={document}
                onDelete={() => handleDelete(document.document_id)}
              />
            ))}
          </div>
          
          <div className="pagination">
            <button 
              onClick={handlePrevPage} 
              disabled={page === 1}
            >
              Previous
            </button>
            <span>Page {page} of {data?.pagination.totalPages}</span>
            <button 
              onClick={handleNextPage} 
              disabled={page >= (data?.pagination.totalPages || 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
};
```

### Chat Implementation

Implement a chat interface with real-time updates:

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { useMutation, useQuery } from 'react-query';
import { chatService } from '../services/chatService';

interface ChatInterfaceProps {
  sessionId: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ sessionId }) => {
  const [message, setMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedResponse, setStreamedResponse] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Fetch chat history
  const { data: chatHistory, refetch: refetchHistory } = useQuery(
    ['chatHistory', sessionId],
    () => chatService.getChatHistory(sessionId)
  );
  
  // Send message mutation
  const sendMessageMutation = useMutation(
    (text: string) => chatService.sendMessage(sessionId, {
      content: text,
      use_rag: true,
      streaming: true,
      rag_options: {
        n_results: 10
      }
    }),
    {
      onSuccess: (response) => {
        setMessage('');
        
        // Handle streaming if enabled
        if (response.headers['x-queue-id']) {
          const queueId = response.headers['x-queue-id'];
          setIsStreaming(true);
          setStreamedResponse('');
          
          // Set up streaming
          const cleanup = chatService.streamChatResponse(
            sessionId,
            queueId,
            (data) => {
              if (data.type === 'token') {
                setStreamedResponse(prev => prev + data.token);
              } else if (data.stage === 'complete') {
                setIsStreaming(false);
                refetchHistory();
              }
            }
          );
          
          // Clean up streaming on component unmount
          return () => cleanup();
        } else {
          // No streaming, just refetch the history
          refetchHistory();
        }
      }
    }
  );
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, streamedResponse]);
  
  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      sendMessageMutation.mutate(message);
    }
  };
  
  return (
    <div className="chat-interface">
      <div className="message-list">
        {chatHistory?.messages.map(msg => (
          <div 
            key={msg.message_id} 
            className={`message ${msg.role === 'user' ? 'user-message' : 'assistant-message'}`}
          >
            <div className="message-content">
              {msg.content}
              
              {msg.citations && msg.citations.length > 0 && (
                <div className="citations">
                  <h4>Sources:</h4>
                  <ul>
                    {msg.citations.map(citation => (
                      <li key={citation.citation_id}>
                        <a href={`/documents/${citation.document_id}?highlight=${citation.chunk_id}`}>
                          {citation.text.substring(0, 100)}...
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <div className="message-metadata">
              {new Date(msg.created_at).toLocaleTimeString()}
            </div>
          </div>
        ))}
        
        {isStreaming && (
          <div className="message assistant-message streaming">
            <div className="message-content">
              {streamedResponse || 'Thinking...'}
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSendMessage} className="message-input">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask a question..."
          disabled={sendMessageMutation.isLoading || isStreaming}
        />
        <button 
          type="submit" 
          disabled={sendMessageMutation.isLoading || isStreaming || !message.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
};
```

### Document Search Implementation

Implement a document search component:

```typescript
import React, { useState } from 'react';
import { useMutation } from 'react-query';
import { documentService } from '../services/documentService';

export const DocumentSearch = () => {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({
    documentType: '',
    tags: []
  });
  
  // Search mutation
  const searchMutation = useMutation(
    (searchQuery: string) => documentService.queryDocuments(
      searchQuery,
      {
        filterCriteria: filters.documentType || filters.tags.length ? {
          document_type: filters.documentType || undefined,
          tags: filters.tags.length ? filters.tags : undefined
        } : undefined,
        nResults: 10
      }
    )
  );
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      searchMutation.mutate(query);
    }
  };
  
  const handleTagClick = (tag: string) => {
    // Toggle tag in filters
    if (filters.tags.includes(tag)) {
      setFilters({
        ...filters,
        tags: filters.tags.filter(t => t !== tag)
      });
    } else {
      setFilters({
        ...filters,
        tags: [...filters.tags, tag]
      });
    }
  };
  
  return (
    <div className="document-search">
      <form onSubmit={handleSearch} className="search-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documents..."
          className="search-input"
        />
        
        <div className="search-filters">
          <select
            value={filters.documentType}
            onChange={(e) => setFilters({ ...filters, documentType: e.target.value })}
          >
            <option value="">All document types</option>
            <option value="pdf">PDF</option>
            <option value="docx">Word</option>
            <option value="pptx">PowerPoint</option>
            <option value="xlsx">Excel</option>
          </select>
          
          <div className="tag-filters">
            {['financial', 'report', 'quarterly', 'marketing'].map(tag => (
              <button
                key={tag}
                type="button"
                className={`tag ${filters.tags.includes(tag) ? 'selected' : ''}`}
                onClick={() => handleTagClick(tag)}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
        
        <button 
          type="submit" 
          className="search-button"
          disabled={searchMutation.isLoading || !query.trim()}
        >
          Search
        </button>
      </form>
      
      <div className="search-results">
        {searchMutation.isLoading ? (
          <div className="loading">Searching...</div>
        ) : searchMutation.error ? (
          <div className="error">Error performing search</div>
        ) : searchMutation.data ? (
          <>
            <h3>Search Results</h3>
            {searchMutation.data.results.length === 0 ? (
              <div className="no-results">No results found</div>
            ) : (
              <ul className="result-list">
                {searchMutation.data.results.map(result => (
                  <li key={result.chunk_id} className="result-item">
                    <div className="result-header">
                      <h4>{result.metadata.source_document_name}</h4>
                      <span className="relevance">
                        Relevance: {((1 - result.distance) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="result-text">{result.text}</p>
                    <div className="result-metadata">
                      {result.metadata.page_number && (
                        <span>Page {result.metadata.page_number}</span>
                      )}
                      <a href={`/documents/${result.document_id}?highlight=${result.chunk_id}`}>
                        View in document
                      </a>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
};
```

## Performance Optimization

1. **Implement pagination** for all list views
2. **Use virtualization** for long lists (react-window or react-virtualized)
3. **Lazy load components** using React.lazy and Suspense
4. **Optimize images** with proper sizing and formats
5. **Memoize expensive calculations** with useMemo
6. **Prevent unnecessary re-renders** with React.memo and useCallback
7. **Implement proper caching** with React Query's caching mechanisms
8. **Use web workers** for intensive client-side calculations

## Deployment Considerations

1. **Build Configuration**
   - Configure optimal build settings for production
   - Implement code splitting
   - Set up environment-specific configurations

2. **Asset Optimization**
   - Compress images and other assets
   - Implement a CDN for static assets
   - Configure proper caching headers

3. **CI/CD Integration**
   - Set up automated builds and deployments
   - Implement quality checks (linting, testing)
   - Configure environment-specific builds

4. **Monitoring**
   - Implement error tracking (Sentry, LogRocket)
   - Set up performance monitoring
   - Track user behavior analytics

## Conclusion

This guide provides a comprehensive framework for developing a frontend application for the DocIntel system. By following these guidelines and patterns, you can create a performant, user-friendly interface that leverages the full capabilities of the DocIntel backend.

Remember to prioritize user experience, maintain a consistent design language, and implement proper error handling throughout the application. Regular testing with real users will help identify areas for improvement and ensure the application meets user needs effectively. 