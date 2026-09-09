/**
 * Capacity Connect — Authentication UI & State Controller
 *
 * Supports Supabase accounts and Django username/password accounts.
 */

'use strict';

const Auth = {
    _currentUser: null,

    async fetchDjangoProfile() {
        try {
            const user = await apiRequest('/auth/me/');
            this._currentUser = user;
            return user;
        } catch (err) {
            this._currentUser = null;
            return null;
        }
    },

    getUser() {
        return this._currentUser;
    },

    async isAuthenticated() {
        const djangoToken = localStorage.getItem('cc_django_token');
        if (djangoToken) return true;

        if (!window.SupabaseAuth) return false;
        const session = await window.SupabaseAuth.getSession();
        return !!(session && session.access_token);
    },

    async login(usernameOrEmail, password) {
        if (window.SupabaseAuth && usernameOrEmail.includes('@')) {
            try {
                const result = await window.SupabaseAuth.signIn(
                    usernameOrEmail,
                    password
                );
                const profile = await this.fetchDjangoProfile();

                if (profile) {
                    return {
                        type: 'supabase',
                        session: result.session,
                        profile,
                    };
                }
            } catch (error) {
                console.info(
                    '[Auth] Supabase login failed; trying Django login.'
                );
            }
        }

        const response = await apiRequest('/auth/login/', {
            method: 'POST',
            skipAuth: true,
            body: JSON.stringify({
                username: usernameOrEmail,
                password,
            }),
        });

        if (!response.token || !response.user) {
            throw new Error('Authentication failed.');
        }

        localStorage.setItem('cc_django_token', response.token);
        this._currentUser = response.user;

        return {
            type: 'django',
            profile: response.user,
        };
    },

    async register(email, password, username, role) {
        if (!window.SupabaseAuth) {
            throw new Error('Supabase Auth client not initialized.');
        }

        const cleanRole = role === 'TRAINER' ? 'TRAINER' : 'TRAINEE';
        return await window.SupabaseAuth.signUp(
            email,
            password,
            username,
            cleanRole
        );
    },

    async logout() {
        localStorage.removeItem('cc_django_token');

        if (window.SupabaseAuth) {
            try {
                await window.SupabaseAuth.signOut();
            } catch (error) {
                console.warn('Supabase logout failed:', error);
            }
        }

        this._currentUser = null;
        this.updateNavbar(null);
        window.location.href = '/index.html';
    },

    async initNavbar() {
        const navContainer =
            document.getElementById('navbarNav') ||
            document.querySelector('.navbar-nav');

        if (!navContainer) return;

        const isAuth = await this.isAuthenticated();

        if (isAuth) {
            const profile = await this.fetchDjangoProfile();
            this.updateNavbar(profile);
        } else {
            this.updateNavbar(null);
        }

        if (window.SupabaseAuth) {
            window.SupabaseAuth.onAuthStateChange(async (event) => {
                if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
                    if (!localStorage.getItem('cc_django_token')) {
                        const profile = await this.fetchDjangoProfile();
                        this.updateNavbar(profile);
                    }
                } else if (
                    event === 'SIGNED_OUT' &&
                    !localStorage.getItem('cc_django_token')
                ) {
                    this._currentUser = null;
                    this.updateNavbar(null);
                }
            });
        }
    },

    updateNavbar(user) {
        const navList = document.getElementById('navbarLinks');
        if (!navList) return;

        if (user) {
            const roleBadgeClass =
                user.role === 'ADMIN'
                    ? 'bg-danger text-white'
                    : (
                        user.role === 'TRAINER'
                            ? 'bg-warning text-dark'
                            : 'bg-info text-dark'
                    );

            navList.innerHTML = `
                <li class="nav-item">
                    <a class="nav-link" href="/index.html"><i class="bi bi-house-door me-1"></i>Home</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link fw-semibold" href="/pages/dashboard.html"><i class="bi bi-speedometer2 me-1"></i>Dashboard</a>
                </li>
                <li class="nav-item dropdown ms-lg-3">
                    <a class="nav-link dropdown-toggle d-flex align-items-center" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="bi bi-person-circle fs-5 me-2"></i>
                        <span>${user.username}</span>
                        <span class="badge ${roleBadgeClass} ms-2">${user.role}</span>
                    </a>
                    <ul class="dropdown-menu dropdown-menu-end shadow-sm">
                        <li><h6 class="dropdown-header">${user.email || user.username}</h6></li>
                        <li>
                            <a class="dropdown-item" href="/pages/dashboard.html">
                                <i class="bi bi-speedometer2 me-2"></i>My Dashboard
                            </a>
                        </li>
                        <li><hr class="dropdown-divider"></li>
                        <li>
                            <a class="dropdown-item text-danger" href="#" id="logoutBtn" onclick="Auth.logout(); return false;">
                                <i class="bi bi-box-arrow-right me-2"></i>Sign Out
                            </a>
                        </li>
                    </ul>
                </li>
            `;
        } else {
            navList.innerHTML = `
                <li class="nav-item">
                    <a class="nav-link" href="/index.html"><i class="bi bi-house-door me-1"></i>Home</a>
                </li>
                <li class="nav-item ms-lg-2">
                    <a class="nav-link btn btn-outline-light px-3 py-1 me-2" href="/pages/login.html">
                        <i class="bi bi-box-arrow-in-right me-1"></i>Log In
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link btn btn-light text-primary px-3 py-1 fw-semibold" href="/pages/register.html">
                        <i class="bi bi-person-plus me-1"></i>Register
                    </a>
                </li>
            `;
        }
    },

    async requireAuth(allowedRoles = []) {
        const isAuth = await this.isAuthenticated();

        if (!isAuth) {
            window.location.href =
                `/pages/login.html?redirect=${encodeURIComponent(
                    window.location.pathname
                )}`;
            return false;
        }

        const profile = await this.fetchDjangoProfile();

        if (!profile) {
            localStorage.removeItem('cc_django_token');
            window.location.href = '/pages/login.html';
            return false;
        }

        if (
            allowedRoles.length > 0 &&
            !allowedRoles.includes(profile.role)
        ) {
            alert(
                `Access denied. This page requires one of the following roles: ${allowedRoles.join(', ')}`
            );
            window.location.href = '/pages/dashboard.html';
            return false;
        }

        return true;
    },

    async redirectIfAuthenticated() {
        const isAuth = await this.isAuthenticated();

        if (isAuth) {
            const profile = await this.fetchDjangoProfile();

            if (profile) {
                window.location.href = '/pages/dashboard.html';
            }
        }
    },
};

window.Auth = Auth;

document.addEventListener('DOMContentLoaded', () => {
    Auth.initNavbar();
});
