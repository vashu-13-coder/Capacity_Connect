/**
 * Capacity Connect — Supabase Configuration Template (supabase-config.example.js)
 *
 * Copy this file to `frontend/js/supabase-config.js` and fill in your actual
 * Supabase Project URL and Public Anon Key.
 */

window.__SUPABASE_URL__ = 'https://<your-project-id>.supabase.co';
window.__SUPABASE_ANON_KEY__ = '<your-public-anon-key>';

if (typeof window !== 'undefined' && window.location) {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (!isLocal) {
        window.__API_BASE_URL__ = 'https://<your-backend-service>.onrender.com/api';
    }
}
