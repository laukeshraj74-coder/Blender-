/**
 * API Client for backend communication
 */

const API_BASE_URL = 'http://127.0.0.1:5000/api';

class APIClient {
    constructor() {
        this.baseUrl = API_BASE_URL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...(options.headers || {})
            }
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // Health check
    async healthCheck() {
        return this.request('/health');
    }

    // Configuration
    async getConfig() {
        return this.request('/config');
    }

    async updateConfig(config) {
        return this.request('/config', {
            method: 'POST',
            body: JSON.stringify(config)
        });
    }

    // AI Provider
    async testAI() {
        return this.request('/test-ai', { method: 'POST' });
    }

    // Blender
    async detectBlender() {
        return this.request('/detect-blender');
    }

    // FFmpeg
    async detectFFmpeg() {
        return this.request('/detect-ffmpeg');
    }

    // Projects
    async listProjects(limit = 50) {
        return this.request(`/projects?limit=${limit}`);
    }

    async createProject(prompt, attachments = []) {
        return this.request('/projects', {
            method: 'POST',
            body: JSON.stringify({ prompt, attachments })
        });
    }

    async getProject(projectId) {
        return this.request(`/projects/${projectId}`);
    }

    async deleteProject(projectId) {
        return this.request(`/projects/${projectId}`, {
            method: 'DELETE'
        });
    }

    // Generation
    async startGeneration(projectId, prompt) {
        return this.request('/generate', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId, prompt })
        });
    }

    async getGenerationStatus() {
        return this.request('/generation/status');
    }

    async cancelGeneration() {
        return this.request('/generation/cancel', { method: 'POST' });
    }

    // File upload
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${this.baseUrl}/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `Upload failed`);
            }

            return data;
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    }
}

// Export singleton instance
window.api = new APIClient();
