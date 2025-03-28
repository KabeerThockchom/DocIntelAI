import { createClient } from '@supabase/supabase-js';

// Get environment variables
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || 'https://opvudlgqcxihuekdpsgo.supabase.co';
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wdnVkbGdxY3hpaHVla2Rwc2dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIwNjMzOTYsImV4cCI6MjA1NzYzOTM5Nn0.ivOfjKLF1vjp-pfxmMiSYtEyMgkV-zU4zM8uri2Msu8';

// Create a single instance of the Supabase client
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Initialize the database schema if needed
export const initializeSchema = async () => {
  try {
    // First check if the table exists
    const { data: tableExists, error: checkError } = await supabase
      .from('user_states')
      .select('count')
      .limit(1)
      .single();

    if (checkError && checkError.code === '42P01') {
      // Table doesn't exist, try to create it
      console.log('user_states table does not exist, attempting to create...');
      
      // Try to create the table using the RPC function
      const { error: rpcError } = await supabase.rpc('create_user_states_if_not_exists');
      
      if (rpcError) {
        console.error('Failed to create table via RPC:', rpcError);
        // If RPC fails, we'll continue with local storage only
        return false;
      }
      
      console.log('Successfully created user_states table');
      return true;
    }
    
    return true;
  } catch (err) {
    console.error('Schema initialization error:', err);
    return false;
  }
};

// Export the client
export default supabase; 