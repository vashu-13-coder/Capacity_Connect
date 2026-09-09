/**
 * Capacity Connect — Main Application JavaScript & API Client
 *
 * Supports Capacity Connect Django tokens and Supabase access tokens.
 */

'use strict';

const APP_CONFIG = {
    get API_BASE_URL() {
        if (window.__API_BASE_URL__) {
            return window.__API_BASE_URL__.replace(/\/+$/, '');
        }
        if (typeof window !== 'undefined' && window.location && window.location.origin) {
            const loc = window.location;
            if (
                loc.port === '8000' ||
                (
                    !['5500', '3000', '5173', '8080'].includes(loc.port) &&
                    loc.protocol.startsWith('http') &&
                    !loc.hostname.includes('127.0.0.1') &&
                    !loc.hostname.includes('localhost')
                )
            ) {
                return `${loc.origin}/api`;
            }
        }
        return 'http://127.0.0.1:8000/api';
    },
    APP_NAME: 'Capacity Connect',
};

async function apiRequest(endpoint, options = {}) {
    const url = `${APP_CONFIG.API_BASE_URL}${endpoint}`;

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (!options.skipAuth) {
        const djangoToken = localStorage.getItem('cc_django_token');

        if (djangoToken) {
            headers.Authorization = `Bearer ${djangoToken}`;
        } else {
            try {
                if (window.SupabaseAuth && window.SupabaseAuth.getSession) {
                    const session = await window.SupabaseAuth.getSession();
                    if (session && session.access_token) {
                        headers.Authorization = `Bearer ${session.access_token}`;
                    }
                }
            } catch (err) {
                console.warn('[API] Could not retrieve Supabase session token:', err);
            }
        }
    }

    const config = {
        ...options,
        headers,
    };

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}`;
            try {
                const errorData = await response.json();
                if (typeof errorData === 'object') {
                    if (errorData.detail) {
                        errorMessage = errorData.detail;
                    } else if (errorData.error) {
                        errorMessage = errorData.error;
                    } else {
                        const messages = Object.entries(errorData)
                            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
                            .join(' | ');
                        errorMessage = messages || errorMessage;
                    }
                }
            } catch (jsonErr) {
                // Response body is not JSON.
            }

            const error = new Error(errorMessage);
            error.status = response.status;
            throw error;
        }

        if (response.status === 204) {
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error(
            `[API] ${options.method || 'GET'} ${endpoint} failed:`,
            error.message
        );
        throw error;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log(`${APP_CONFIG.APP_NAME} initialized.`);
});
