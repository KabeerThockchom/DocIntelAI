import axios from 'axios';
import supabase from './supabaseClient';

// Get the API base URL from environment variables or use the production URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://docintel.fly.dev/api';
console.log('Using API base URL:', API_BASE_URL);

// Create an axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor for handling auth tokens
api.interceptors.request.use(
  async (config) => {
    try {
      // Get the current session from Supabase
      const { data } = await supabase.auth.getSession();
      const session = data.session;

      console.log('Request URL:', config.url);
      console.log('Request Headers:', config.headers);

      // If we have a session, include the auth token
      if (session) {
        config.headers['Authorization'] = `Bearer ${session.access_token}`;
        // Add user_id to headers for role-based access control
        config.headers['X-User-ID'] = session.user.id;
        console.log('Added auth headers for user:', session.user.id);
      } else {
        console.log('No active session found');
      }
    } catch (error) {
      console.error('Error getting auth token:', error);
    }
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Add a response interceptor for handling errors
api.interceptors.response.use(
  (response) => {
    // Check if the response is likely HTML when expecting JSON
    const contentType = response.headers['content-type'] || '';
    if (contentType.includes('text/html') && 
        !response.config.url?.includes('/stream/') && 
        response.config.responseType !== 'text') {
      console.warn('Received HTML when expecting JSON. This might cause parsing errors.');
      // You could throw an error here or transform the response
      return Promise.reject(new Error('Received HTML response when expecting JSON'));
    }
    return response;
  },
  async (error) => {
    // Handle common errors here
    if (error.response) {
      const contentType = error.response.headers?.['content-type'] || '';
      if (contentType.includes('text/html')) {
        console.error('Received HTML error response instead of JSON:', 
          error.response.status, 
          error.response.statusText);
        return Promise.reject(new Error(`Received HTML error (${error.response.status}): ${error.response.statusText}`));
      }
      
      // Handle unauthorized errors (could be expired token)
      if (error.response.status === 401) {
        console.error('Authentication error. You may need to log in again.');
        
        // Optionally, you could sign out here if token is invalid
        // await supabase.auth.signOut();
        
        // Redirect to login page
        // window.location.href = '/login';
      } else if (error.response.status === 404) {
        console.error('Resource not found:', error.config.url);
      } else {
        console.error('API Error:', error.response.data);
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Network Error:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Request Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default api; 