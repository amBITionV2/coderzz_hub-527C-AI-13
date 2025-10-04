/**
 * Centralized API client for FloatChat backend communication
 */

// TypeScript interfaces for API responses
export interface QueryParameters {
  location?: string | null;
  bbox?: number[] | null;
  start_date?: string | null;
  end_date?: string | null;
  variables: string[];
  depth_range?: number[] | null;
  general_search_term?: string | null;
}

export interface FloatSummary {
  id: number;
  wmo_id: string;
  latitude?: number | null;
  longitude?: number | null;
  status: 'active' | 'inactive' | 'maintenance';
  last_update?: string | null;
  profile_count: number;
  latest_profile_date?: string | null;
}

export interface MeasurementSchema {
  id: number;
  profile_id: number;
  pressure: number;
  depth?: number | null;
  temperature?: number | null;
  salinity?: number | null;
  dissolved_oxygen?: number | null;
  ph?: number | null;
  nitrate?: number | null;
  chlorophyll?: number | null;
  measurement_order: number;
  created_at: string;
  updated_at: string;
}

export interface ProfileSchema {
  id: number;
  float_id: number;
  cycle_number: number;
  profile_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  direction: 'A' | 'D';
  data_mode: 'R' | 'A' | 'D';
  measurements: MeasurementSchema[];
  created_at: string;
  updated_at: string;
}

export interface FloatDetail {
  id: number;
  wmo_id: string;
  deployment_latitude?: number | null;
  deployment_longitude?: number | null;
  platform_type?: string | null;
  institution?: string | null;
  project_name?: string | null;
  pi_name?: string | null;
  status: 'active' | 'inactive' | 'maintenance';
  deployment_date?: string | null;
  last_update?: string | null;
  profiles: ProfileSchema[];
  created_at: string;
  updated_at: string;
}

export interface AIQueryResponse {
  query: string;
  parameters: QueryParameters;
  floats: FloatSummary[];
  insights: string;
  data_summary: Record<string, any>;
  recommendations: string[];
  processing_time: number;
}

export interface APIError {
  error: string;
  message: string;
  details?: any;
}

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_TIMEOUT = parseInt(import.meta.env.VITE_API_TIMEOUT || '30000');
const API_DEBUG = import.meta.env.VITE_API_DEBUG === 'true';

// Custom error class for API errors
export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Generic API request function with error handling
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Default headers
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  // Merge headers
  const headers = {
    ...defaultHeaders,
    ...options.headers,
  };

  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    if (API_DEBUG) {
      console.log(`[API] ${options.method || 'GET'} ${url}`, {
        headers,
        body: options.body,
      });
    }

    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle non-JSON responses
    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
      throw new APIError(
        `Invalid response format: ${contentType}`,
        response.status
      );
    }

    const data = await response.json();

    if (!response.ok) {
      // Handle API error responses
      const errorMessage = data.message || data.error || `HTTP ${response.status}`;
      throw new APIError(errorMessage, response.status, data);
    }

    if (API_DEBUG) {
      console.log(`[API] Response:`, data);
    }

    return data;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      throw new APIError('Request timeout', 408);
    }

    if (error instanceof APIError) {
      throw error;
    }

    // Network or other errors
    throw new APIError(
      error.message || 'Network error occurred',
      0,
      error
    );
  }
}

/**
 * Post a natural language query to the AI endpoint
 * @param question - Natural language question about oceanographic data
 * @returns Promise<AIQueryResponse> - AI-processed response with floats and insights
 */
export async function postQuery(question: string): Promise<AIQueryResponse> {
  if (!question.trim()) {
    throw new APIError('Question cannot be empty');
  }

  return apiRequest<AIQueryResponse>('/api/v1/query', {
    method: 'POST',
    body: JSON.stringify({
      question: question.trim(),
      context: {
        timestamp: new Date().toISOString(),
        source: 'web_frontend'
      }
    }),
  });
}

/**
 * Fetch detailed float data by WMO ID
 * @param wmoId - WMO identifier of the float
 * @returns Promise<FloatDetail> - Complete float data with profiles and measurements
 */
export async function fetchFloatById(wmoId: string): Promise<FloatDetail> {
  if (!wmoId.trim()) {
    throw new APIError('WMO ID cannot be empty');
  }

  // Validate WMO ID format (basic validation)
  if (!/^\d+$/.test(wmoId.trim())) {
    throw new APIError('Invalid WMO ID format. Must be numeric.');
  }

  return apiRequest<FloatDetail>(`/api/v1/float/${encodeURIComponent(wmoId.trim())}`);
}

/**
 * Fetch float summary data (for listings)
 * @param params - Query parameters for filtering
 * @returns Promise<FloatSummary[]> - Array of float summaries
 */
export async function fetchFloats(params: {
  page?: number;
  size?: number;
  status?: string;
  wmo_id?: string;
} = {}): Promise<{
  items: FloatSummary[];
  total: number;
  page: number;
  size: number;
  pages: number;
}> {
  const searchParams = new URLSearchParams();
  
  if (params.page) searchParams.set('page', params.page.toString());
  if (params.size) searchParams.set('size', params.size.toString());
  if (params.status) searchParams.set('status', params.status);
  if (params.wmo_id) searchParams.set('wmo_id', params.wmo_id);

  const queryString = searchParams.toString();
  const endpoint = `/api/v1/floats${queryString ? `?${queryString}` : ''}`;

  return apiRequest(endpoint);
}

/**
 * Health check endpoint
 * @returns Promise<{status: string, timestamp: string, database: boolean, version: string}>
 */
export async function healthCheck(): Promise<{
  status: string;
  timestamp: string;
  database: boolean;
  version: string;
}> {
  return apiRequest('/health');
}

// Export API configuration for use in components
export const API_CONFIG = {
  BASE_URL: API_BASE_URL,
  TIMEOUT: API_TIMEOUT,
  DEBUG: API_DEBUG,
} as const;
