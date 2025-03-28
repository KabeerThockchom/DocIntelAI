import api from './api';

// Types
export interface ChatSessionCreate {
  title: string;
  user_id: string;
  metadata?: Record<string, any>;
}

export interface ChatSessionResponse {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  user_id: string;
  metadata: Record<string, any>;
}

export interface ChatSessionListResponse {
  sessions: ChatSessionResponse[];
  total_count: number;
}

export interface SendMessageRequest {
  content: string;
  metadata?: Record<string, any>;
  use_retrieval?: boolean | null;
  stream_processing?: boolean;
  include_history: boolean;
}

export interface Citation {
  citation_id: string;
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number?: number;
  text_snippet: string;
  relevance_score: number;
  is_cited?: boolean;
  bounding_box?: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    page?: number;
  };
}

export interface MessageResponse {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  citations: Citation[];
  metadata: Record<string, any>;
}

export interface ChatHistoryResponse {
  session_id: string;
  title: string;
  messages: MessageResponse[];
  metadata: Record<string, any>;
}

// Processing stage types for the loading animation
export type ProcessingStage = 
  | 'analyzing_query' 
  | 'deciding_retrieval' 
  | 'splitting_query' 
  | 'retrieving_documents' 
  | 'generating_answer' 
  | 'complete';

export interface ProcessingUpdate {
  stage: ProcessingStage;
  message: string;
  details?: {
    isFollowUp?: boolean;
    previousQuery?: string;
    [key: string]: any;
  };
  queue_id?: string;
  subQueries?: string[];
  isCompleted: boolean;
  steps?: string[];           // Array of step names for the current stage
  current_step?: string;      // The currently executing step
  completed_steps?: string[]; // List of steps that have been completed
}

// Chat API functions
export const chatService = {
  // Create a chat session
  createChatSession: async (sessionData: ChatSessionCreate) => {
    const response = await api.post('/chat/sessions', sessionData);
    return response.data as ChatSessionResponse;
  },
  
  // List chat sessions
  listChatSessions: async (userId?: string, skip: number = 0, limit: number = 10) => {
    const params: Record<string, any> = { skip, limit };
    
    if (userId) {
      params.user_id = userId;
    }
    
    const response = await api.get('/chat/sessions', { params });
    return response.data as ChatSessionListResponse;
  },
  
  // Get a chat session
  getChatSession: async (sessionId: string) => {
    const response = await api.get(`/chat/sessions/${sessionId}`);
    return response.data as ChatSessionResponse;
  },
  
  // Delete a chat session
  deleteChatSession: async (sessionId: string) => {
    const response = await api.delete(`/chat/sessions/${sessionId}`);
    return response.data;
  },
  
  // Get chat history
  getChatHistory: async (sessionId: string) => {
    const response = await api.get(`/chat/sessions/${sessionId}/messages`);
    return response.data as ChatHistoryResponse;
  },
  
  // Send a message with processing updates using SSE
  sendMessageWithUpdates: async (
    sessionId: string, 
    message: SendMessageRequest, 
    onUpdate: (update: ProcessingUpdate) => void,
    parallelProcessing: boolean = true
  ) => {
    try {
      // First, check if session exists before sending message
      try {
        await api.get(`/chat/sessions/${sessionId}`);
      } catch (error) {
        console.error('Chat session not found:', sessionId);
        onUpdate({
          stage: 'complete',
          message: 'Error: Chat session not found',
          details: { error: true },
          isCompleted: true
        });
        throw error;
      }
      
      // Send initial update to show we're processing
      onUpdate({
        stage: 'analyzing_query',
        message: 'Analyzing your query...',
        details: {},
        isCompleted: false
      });
      
      // Create a unique queue ID on the client side
      const clientQueueId = `${sessionId}_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
      console.log('Generated client-side queue ID:', clientQueueId);
      
      // Ensure include_history is true to fix context retention issues
      if (message.include_history === undefined) {
        message.include_history = true;
      }
      
      // Set up SSE connection BEFORE sending the message
      let eventSource: EventSource | null = null;
      let sseConnected = false;
      
      // Set up EventSource connection
      const connectSSE = () => {
        try {
          // Define realtime flag - prefer realtime stream for better performance
          const useRealtimeStream = true;
          
          // Get the API base URL
          const apiUrl = api.defaults.baseURL || '';
          
          // Use the realtime endpoint for better streaming performance
          const streamEndpoint = useRealtimeStream ? 
            `/chat/sessions/${sessionId}/realtime-stream/${clientQueueId}` :
            `/chat/sessions/${sessionId}/stream/${clientQueueId}`;
          
          console.log(`Connecting to SSE BEFORE sending message: ${apiUrl}${streamEndpoint}`);
          
          // Create new EventSource connection
          eventSource = new EventSource(`${apiUrl}${streamEndpoint}`);
          
          // Handle connection open
          eventSource.onopen = () => {
            console.log('SSE connection opened successfully (before message sent)');
            sseConnected = true;
          };
          
          // Handle incoming events
          eventSource.onmessage = (event) => {
            try {
              // Skip processing flush comments
              if (event.data.startsWith(':')) {
                return;
              }
              
              console.log('[SSE Event Received]:', event.type, 'Length:', event.data.length);
              
              // Validate that data is not empty
              if (!event.data || event.data.trim() === '') {
                console.warn('[SSE Warning] Empty data received');
                return;
              }
              
              const data = JSON.parse(event.data);
              console.log('[SSE Parsed Event]:', data);
              
              // Check if this is an error message from the server
              if (data.type === 'error' && data.error === true) {
                console.error('[SSE Server Error]:', data.message || 'Unknown server error');
                
                // If the stream wasn't found, switch to fallback
                if (data.code === 404) {
                  console.warn('Stream not found on server, switching to fallback');
                  performFallbackPolling(sessionId, message.content);
                  if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                  }
                  return;
                }
              }
              
              // Handle different event types
              if (data.type === 'processing_update') {
                // Process update event immediately
                console.log('[Processing Update Event]:', JSON.stringify(data));
                
                // Create update object, ensuring isCompleted is a boolean
                const update: ProcessingUpdate = {
                  stage: data.stage,
                  message: data.message || 'Processing...',
                  details: data.details || {},
                  isCompleted: data.isCompleted === true,
                  steps: data.steps || [],
                  current_step: data.current_step || null,
                  completed_steps: data.completed_steps || []
                };
                
                // Add subQueries if available in the splitting_query stage
                if (data.stage === 'splitting_query') {
                  // Handle subQueries directly from the data
                  if (data.subQueries && Array.isArray(data.subQueries) && data.subQueries.length > 0) {
                    update.subQueries = data.subQueries;
                  }
                  // Support multiple formats of sub-queries for backward compatibility
                  else if (data.details && data.details.sub_queries && Array.isArray(data.details.sub_queries) && data.details.sub_queries.length > 0) {
                    update.subQueries = data.details.sub_queries;
                  }
                  else if (data.details && data.details.subQueries && Array.isArray(data.details.subQueries) && data.details.subQueries.length > 0) {
                    update.subQueries = data.details.subQueries;
                  }
                }
                
                // Immediately invoke the callback
                onUpdate(update);
                
                // If complete, close the connection
                if (data.stage === 'complete') {
                  console.log('[Complete stage] Closing EventSource connection');
                  if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                  }
                }
              } else if (data.type === 'heartbeat' || data.type === 'keepalive') {
                // Just a keepalive
                console.log(`Received ${data.type} at ${new Date().toISOString()}`);
              } else if (data.type === 'connection_established') {
                console.log('SSE connection established event received');
              } else {
                console.log('Unknown event type received:', data.type);
              }
            } catch (error) {
              console.error('Error parsing SSE event:', error, 'Raw data:', event.data);
              
              // Notify about the parsing error
              onUpdate({
                stage: 'complete',
                message: 'Error: Failed to parse server response',
                details: { error: true, parseError: true },
                isCompleted: true
              });
              
              // Close the connection on parse error
              if (eventSource) {
                eventSource.close();
                eventSource = null;
              }
            }
          };
          
          // Handle errors with more robust approach
          let retryCount = 0;
          const maxRetries = 2;
          const retryDelay = 500;
          
          eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            
            // If connection was never established or was lost
            if (!sseConnected || retryCount < maxRetries) {
              retryCount++;
              const currentDelay = retryDelay * Math.pow(1.5, retryCount);
              
              console.log(`Connection error. Retrying (${retryCount}/${maxRetries}) in ${currentDelay/1000}s...`);
              
              // Close existing connection
              if (eventSource) {
                eventSource.close();
                eventSource = null;
              }
              
              // Show reconnecting message
              onUpdate({
                stage: sseConnected ? 'retrieving_documents' : 'analyzing_query',
                message: `Connection interrupted. Retrying (${retryCount}/${maxRetries})...`,
                details: { reconnecting: true },
                isCompleted: false
              });
              
              // Try again after a delay with exponential backoff
              setTimeout(() => {
                // Check if we've lost connection too many times, switch to fallback
                if (retryCount >= 2) {
                  console.warn('Multiple connection failures, switching to fallback');
                  performFallbackPolling(sessionId, message.content);
                } else {
                  connectSSE();
                }
              }, currentDelay);
              
              return;
            }
            
            // If we've exhausted retries, use a fallback approach - query for result directly
            console.warn('SSE connection failed after max retries, falling back to direct query');
            performFallbackPolling(sessionId, message.content);
          };
        } catch (sseError) {
          console.error('Error creating EventSource connection:', sseError);
          performFallbackPolling(sessionId, message.content);
        }
      };
      
      // Function to handle fallback polling when SSE fails
      const performFallbackPolling = async (sid: string, query: string) => {
        console.log('Using fallback polling mechanism');
        
        onUpdate({
          stage: 'analyzing_query',
          message: 'Processing your query...',
          details: { fallback: true },
          isCompleted: false
        });
        
        // Wait a bit to allow backend processing
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Then poll for the result
        try {
          // Poll the chat history to get the result
          const history = await chatService.getChatHistory(sid);
          const messages = history.messages;
          
          // Find the assistant's response to our query (should be the last one)
          const latestUserMsg = messages.filter(m => m.role === 'user').pop();
          const latestAssistantMsg = messages.filter(m => m.role === 'assistant').pop();
          
          if (latestAssistantMsg && latestUserMsg && latestUserMsg.content === query) {
            // We found a matching response
            onUpdate({
              stage: 'complete',
              message: 'Response generated',
              details: { fallback: true, complete: true },
              isCompleted: true
            });
          } else {
            // No response found yet, simulate stages
            onUpdate({
              stage: 'retrieving_documents',
              message: 'Searching for information...',
              details: { fallback: true },
              isCompleted: false
            });
            
            // Wait a bit more and try again
            setTimeout(async () => {
              try {
                const updatedHistory = await chatService.getChatHistory(sid);
                const updatedMessages = updatedHistory.messages;
                const finalAssistantMsg = updatedMessages.filter(m => m.role === 'assistant').pop();
                
                if (finalAssistantMsg) {
                  onUpdate({
                    stage: 'complete',
                    message: 'Response generated',
                    details: { fallback: true, complete: true },
                    isCompleted: true
                  });
                } else {
                  onUpdate({
                    stage: 'complete',
                    message: 'Could not retrieve response',
                    details: { error: true, fallback: true },
                    isCompleted: true
                  });
                }
              } catch (finalErr) {
                onUpdate({
                  stage: 'complete',
                  message: 'Error retrieving response',
                  details: { error: true, fallback: true },
                  isCompleted: true
                });
              }
            }, 5000);
          }
        } catch (pollErr) {
          console.error('Error in fallback polling:', pollErr);
          onUpdate({
            stage: 'complete',
            message: 'Error processing your request',
            details: { error: true, fallback: true },
            isCompleted: true
          });
        }
      };
      
      // Connect to SSE first
      connectSSE();
      
      // Prepare request params
      const params = { parallel_processing: parallelProcessing };
      
      // Add the client-generated queue ID to the message metadata
      const messageWithQueue = {
        ...message,
        stream_processing: true,
        metadata: {
          ...(message.metadata || {}),
          queue_id: clientQueueId
        }
      };
      
      // AFTER establishing the SSE connection, send the message
      console.log('Sending message with client-side queue ID:', clientQueueId);
      const response = await api.post(
        `/chat/sessions/${sessionId}/messages`, 
        messageWithQueue, 
        { 
          params,
          headers: {
            'X-Client-Queue-ID': clientQueueId  // Send the queue ID in a header too
          }
        }
      );
      
      console.log('Message sent, response received');
      
      return response.data as MessageResponse;
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Notify about the error
      onUpdate({
        stage: 'complete',
        message: 'Error sending message',
        details: { error: true },
        isCompleted: true
      });
      
      throw error;
    }
  },
  
  // Send a message
  sendMessage: async (sessionId: string, message: SendMessageRequest, parallelProcessing: boolean = true) => {
    const params = { parallel_processing: parallelProcessing };
    const response = await api.post(`/chat/sessions/${sessionId}/messages`, message, { params });
    return response.data as MessageResponse;
  },
  
  // Batch send messages (using parallel processing)
  batchSendMessages: async (sessionId: string, messages: SendMessageRequest[]) => {
    const response = await api.post(`/chat/batch/messages?session_id=${sessionId}`, messages);
    return response.data as MessageResponse[];
  },
  
  // Get a message
  getMessage: async (messageId: string) => {
    const response = await api.get(`/chat/messages/${messageId}`);
    return response.data as MessageResponse;
  },
  
  // Get message citations
  getMessageCitations: async (messageId: string) => {
    const response = await api.get(`/chat/messages/${messageId}/citations`);
    return response.data.citations as Citation[];
  },
  
  // Get citation source
  getCitationSource: async (documentId: string, chunkId: string) => {
    const response = await api.get(`/chat/citations/${documentId}/${chunkId}`);
    return response.data;
  },
  
  // Export chat session
  exportChatSession: async (sessionId: string, includeCitations: boolean = true) => {
    const params = { include_citations: includeCitations };
    const response = await api.get(`/chat/sessions/${sessionId}/export`, { params });
    return response.data;
  }
};

export default chatService; 