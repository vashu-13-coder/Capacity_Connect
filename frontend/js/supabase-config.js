/**
 * Capacity Connect — Client Configuration
 */

// Supabase Authentication & Storage
window.__SUPABASE_URL__ = 'https://jnevchtixesdwwkbjkez.supabase.co';
window.__SUPABASE_ANON_KEY__ = 'sb_publishable_2kEliSLuDrkCmNuQ-rBZqw_dA7N3rPV';

// API configuration
// Local development uses Django directly. Production uses the Render backend
// directly so authentication requests do not depend on Vercel rewrite matching.
if (typeof window !== 'undefined' && window.location) {
    const isLocal = window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1';

    window.__API_BASE_URL__ = isLocal
        ? 'http://127.0.0.1:8000/api'
        : 'https://capacity-connect-bdxd.onrender.com/api';
}
