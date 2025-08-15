// API utility functions for the Computer Use Interface

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(message, status, response) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.response = response;
  }
}

async function handleResponse(response) {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.error || errorData.detail || errorMessage;
    } catch {
      // If we can't parse the error response, use the default message
    }
    throw new ApiError(errorMessage, response.status, response);
  }
  
  return response.json();
}

export const api = {
  // Session management
  async createSession() {
    const response = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return handleResponse(response);
  },

  async getSessions() {
    const response = await fetch(`${API_BASE}/sessions`);
    return handleResponse(response);
  },

  async getSession(sessionId) {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
    return handleResponse(response);
  },

  async deleteSession(sessionId) {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },

  // Message management
  async sendMessage(sessionId, messageData) {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        ...messageData,
      }),
    });
    return handleResponse(response);
  },

  // Health checks
  async checkHealth() {
    const response = await fetch(`${API_BASE}/health`);
    return handleResponse(response);
  },

  async checkDatabaseHealth() {
    const response = await fetch(`${API_BASE}/health/db`);
    return handleResponse(response);
  },

  async checkRedisHealth() {
    const response = await fetch(`${API_BASE}/health/redis`);
    return handleResponse(response);
  },
};

export { ApiError };