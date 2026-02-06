/**
 * Shared API utilities for backend communication.
 */

const API = {
    async request(url, options = {}) {
        const token = localStorage.getItem('access_token');
        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options.headers,
        };

        const response = await fetch(url, { ...options, headers });

        if (response.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = '/static/index.html';
            return null;
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || 'Request failed');
        }

        return response.json();
    },

    get(url) {
        return this.request(url, { method: 'GET' });
    },

    post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    getMe() {
        return this.get('/auth/me');
    },

    updateProfile(data) {
        return this.request('/auth/me', {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    async uploadAvatar(file) {
        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const res = await fetch('/auth/me/profile-picture', {
            method: 'POST',
            headers: {
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            },
            body: formData
        });

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Upload failed' }));
            throw new Error(error.detail || 'Upload failed');
        }

        return res.json();
    },

    async login(username, password) {
        const res = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username, password })
        });

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Login failed' }));
            throw new Error(error.detail || 'Login failed');
        }

        const data = await res.json();
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user_id', data.user_id);
        return data;
    },

    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_id');
        window.location.href = '/static/index.html';
    },

    isAuthenticated() {
        return !!localStorage.getItem('access_token');
    }
};

export default API;
