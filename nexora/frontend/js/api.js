/**
 * Nexora API Client — Adapted for /api/v1/* endpoints
 * Based on Odysseus api.js with Nexora-specific endpoints
 *
 * Base URL resolution order:
 *   1. `?api=` query parameter            (?api=http://localhost:8000/api/v1)
 *   2. `window.NEXORA_API_BASE`
 *   3. same-origin `/api/v1`
 *
 * `setBaseUrl()` lets the app repoint the client at the backend port when the
 * UI is served by a separate static server (the default `python -m http.server`
 * dev setup on :3000).
 */

function resolveBaseUrl() {
  try {
    const fromQuery = new URLSearchParams(window.location.search).get('api');
    if (fromQuery) return fromQuery.replace(/\/+$/, '');
  } catch {
    /* no search params available */
  }
  if (window.NEXORA_API_BASE) return String(window.NEXORA_API_BASE).replace(/\/+$/, '');
  return '/api/v1';
}

class ApiClient {
  constructor(baseUrl = resolveBaseUrl()) {
    this.baseUrl = baseUrl;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  /** Repoint every typed helper at a new base (used by the boot-time probe). */
  setBaseUrl(baseUrl) {
    this.baseUrl = String(baseUrl || '').replace(/\/+$/, '') || '/api/v1';
    return this.baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: { ...this.defaultHeaders, ...options.headers },
      ...options,
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      
      const contentType = response.headers.get('content-type');
      let data;
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        throw this.normalizeError(response, data);
      }

      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      // A TypeError out of fetch() means either the connection was refused or
      // the browser refused to expose the response. The second case is the
      // misleading one: an unhandled server-side exception produces a 500 with
      // no Access-Control-Allow-Origin header (FastAPI's CORSMiddleware sits
      // inside ServerErrorMiddleware), so the browser reports the opaque
      // failure as a plain network error even though the backend did reply.
      const detail = error && error.message ? error.message : String(error);
      throw new ApiError(
        `Cannot reach the Nexora API at ${this.baseUrl}. If the backend is up, ` +
        'this is a cross-origin rejection — check the backend log for a traceback.',
        0,
        'NETWORK_ERROR',
        detail
      );
    }
  }

  normalizeError(response, data) {
    let message = 'Request failed';
    let code = 'UNKNOWN_ERROR';
    let details = null;

    if (typeof data === 'object' && data !== null) {
      message = data.detail || data.message || message;
      code = data.code || code;
      details = data.details || null;
    } else if (typeof data === 'string') {
      message = data;
    }

    return new ApiError(message, response.status, code, details);
  }

  // Convenience methods
  get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url, { method: 'GET' });
  }

  post(endpoint, body) {
    return this.request(endpoint, { method: 'POST', body });
  }

  patch(endpoint, body) {
    return this.request(endpoint, { method: 'PATCH', body });
  }

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

class ApiError extends Error {
  constructor(message, status, code, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Singleton instance
const api = new ApiClient();

// Export for use in other modules
window.NexoraApi = api;
window.ApiError = ApiError;
window.ApiClient = ApiClient;

// ============================================================
// Typed API Methods — Mapped to Nexora Backend Endpoints
// ============================================================

// Workspaces
api.workspaces = {
  list: (params = {}) => api.get('/workspaces', params),
  get: (id) => api.get(`/workspaces/${id}`),
  create: (data) => api.post('/workspaces', data),
  update: (id, data) => api.patch(`/workspaces/${id}`, data),
  delete: (id) => api.delete(`/workspaces/${id}`),
};

// Budget Profiles
api.budgetProfiles = {
  list: () => api.get('/budget-profiles'),
  get: (id) => api.get(`/budget-profiles/${id}`),
  create: (data) => api.post('/budget-profiles', data),
  update: (id, data) => api.patch(`/budget-profiles/${id}`, data),
};

// Models
api.models = {
  list: (enabledOnly = true) => api.get('/models', { enabled_only: enabledOnly }),
  get: (id) => api.get(`/models/${id}`),
  create: (data) => api.post('/models', data),
  update: (id, data) => api.patch(`/models/${id}`, data),
};

// Runs (Nexora's equivalent of sessions)
api.runs = {
  list: (params = {}) => api.get('/runs', params),
  get: (id) => api.get(`/runs/${id}`),
  create: (data) => api.post('/runs', data),
  update: (id, data) => api.patch(`/runs/${id}`, data),
  start: (id) => api.post(`/runs/${id}/start`),
  approve: (id, approvalId, approve) => api.post(`/runs/${id}/approve`, { approval_id: approvalId, approve }),
  cancel: (id) => api.post(`/runs/${id}/cancel`),
};

// Policy Decisions
api.policyDecisions = {
  list: (runId) => api.get(`/runs/${runId}/policy-decisions`),
  get: (id) => api.get(`/policy-decisions/${id}`),
};

// Tool Requests
api.toolRequests = {
  list: (runId) => api.get(`/runs/${runId}/tool-requests`),
  get: (id) => api.get(`/tool-requests/${id}`),
};

// Tool Executions
api.toolExecutions = {
  list: (runId) => api.get(`/runs/${runId}/tool-executions`),
  get: (id) => api.get(`/tool-executions/${id}`),
};

// Approvals
api.approvals = {
  list: (runId) => api.get(`/runs/${runId}/approvals`),
  get: (id) => api.get(`/approvals/${id}`),
  decide: (id, approve) => api.post(`/approvals/${id}/decide`, { approve }),
};

// Audit Events
api.auditEvents = {
  list: (runId) => api.get(`/runs/${runId}/audit-events`),
};

// Context
api.context = {
  get: (runId) => api.get(`/runs/${runId}/context`),
  compact: (runId) => api.post(`/runs/${runId}/compact`),
};

// Health
api.health = () => api.get('/health');

// Legacy session compatibility (maps to runs)
api.sessions = {
  list: (params = {}) => api.get('/runs', params),
  get: (id) => api.get(`/runs/${id}`),
  create: (data) => api.post('/runs', data),
  update: (id, data) => api.patch(`/runs/${id}`, data),
};

export { api, ApiError, ApiClient };