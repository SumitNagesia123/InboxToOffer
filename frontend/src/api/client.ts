/**
 * API Client with JWT authorization and standardized error handling.
 */

const BASE_URL = '/api/v1';

export interface ApiError {
  code: string;
  message: string;
  details?: any;
}

export class ApiException extends Error {
  code: string;
  details?: any;
  status: number;

  constructor(message: string, code: string = 'API_ERROR', status: number = 500, details?: any) {
    super(message);
    this.name = 'ApiException';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const token = localStorage.getItem('aijob_token');

  // Prevent sending unauthenticated requests to protected endpoints
  if (!token && !endpoint.startsWith('/auth/')) {
    if (typeof window !== 'undefined' && !window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
      const redirectUrl = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?session_expired=true&redirect=${redirectUrl}`;
    }
    throw new ApiException('Authentication token is missing. Please log in.', 'UNAUTHORIZED', 401);
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Handle FormData where browser needs to set boundary
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    // If unauthenticated, clear token and auto-redirect to login
    if (response.status === 401) {
      localStorage.removeItem('aijob_token');
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
        const redirectUrl = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/login?session_expired=true&redirect=${redirectUrl}`;
      }
    }

    const errorData = data.error || {};
    throw new ApiException(
      errorData.message || response.statusText || 'An unexpected error occurred',
      errorData.code || `HTTP_${response.status}`,
      response.status,
      errorData.details
    );
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'GET', ...options }),

  post: <T>(endpoint: string, body?: any, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
      ...options,
    }),

  patch: <T>(endpoint: string, body?: any, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body),
      ...options,
    }),

  delete: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'DELETE', ...options }),
};
