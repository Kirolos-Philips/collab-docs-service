/**
 * Utility functions for presence and UI.
 */

export const Utils = {
    /**
     * Generate a unique color based on ID (fallback).
     */
    getColor(id) {
        const colors = ["#2563eb", "#10b981", "#ef4444", "#f59e0b", "#8b5cf6", "#ec4899"];
        let hash = 0;
        for (let i = 0; i < id.length; i++) {
            hash = id.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    },

    /**
     * Sanitize text.
     */
    escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
