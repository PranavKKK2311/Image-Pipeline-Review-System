// API configuration for development and production
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const api = {
    baseUrl: API_BASE_URL,

    async fetch(endpoint: string, options: RequestInit = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        return fetch(url, options);
    },

    // Get full URL for images
    getImageUrl(path: string): string {
        if (!path) return '';
        if (path.startsWith('http://') || path.startsWith('https://')) {
            return path;
        }
        if (path.startsWith('/uploads/')) {
            return `${API_BASE_URL}${path}`;
        }
        return path;
    }
};

export default api;
