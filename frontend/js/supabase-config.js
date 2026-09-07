/**
 * Capacity Connect — Client Configuration
 */

// Supabase Authentication & Storage
window.__SUPABASE_URL__ = 'https://jnevchtixesdwwkbjkez.supabase.co';
window.__SUPABASE_ANON_KEY__ = 'sb_publishable_2kEliSLuDrkCmNuQ-rBZqw_dA7N3rPV';

// Single-domain configuration:
// - In local dev (localhost/127.0.0.1): connects to http://127.0.0.1:8000/api
// - In production (Vercel): connects to same-origin /api (proxied to Render by Vercel)
if (typeof window !== 'undefined' && window.location) {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (!isLocal) {
        window.__API_BASE_URL__ = window.location.origin + '/api';
    }
}
