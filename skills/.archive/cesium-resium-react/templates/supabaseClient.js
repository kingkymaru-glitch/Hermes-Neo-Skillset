import { createClient } from '@supabase/supabase-js'

// Vite only exposes VITE_-prefixed vars to the browser bundle.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Null-safe: missing creds => null client so the app degrades to demo data
// instead of throwing at import time.
export const supabase =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey)
    : null

export const isSupabaseConfigured = Boolean(supabase)
