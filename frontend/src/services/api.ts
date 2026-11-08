
// Centralized Frontend HTTP Client 


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Optional runtime auth/tenant context headers 
let authToken: string | null = null;
let selectedOrgId: string | null = null;

export function setApiAuthContext(token: string | null, orgId: string | null) {
  authToken = token;
  selectedOrgId = orgId;
}

function buildHeaders(isMultipart = false, customHeaders?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {};
  if (!isMultipart) {
    headers['Content-Type'] = 'application/json';
  }
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  if (selectedOrgId) {
    headers['X-Demo-Org-Id'] = selectedOrgId;
  }
  return {
    ...headers,
    ...(customHeaders as Record<string, string>),
  };
}

async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const data = await response.json();
    // Section 15: Handle structured domain errors { detail: { error, message } }
    if (data?.detail) {
      if (typeof data.detail === 'string') return data.detail;
      if (data.detail.message) {
        return `${data.detail.error || 'ERROR'}: ${data.detail.message}`;
      }
      if (Array.isArray(data.detail)) {
        return data.detail.map((d: { msg?: string }) => d.msg || 'Validation error').join('; ');
      }
    }
    return `HTTP ${response.status}: Request failed`;
  } catch {
    return `HTTP ${response.status}: ${response.statusText || 'Network error'}`;
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: buildHeaders(false, options?.headers),
  });

  if (!response.ok) {
    const msg = await parseErrorResponse(response);
    throw new Error(msg);
  }

  return response.json() as Promise<T>;
}

// Section 2.2: Multipart upload helper (Browser sets multipart boundary automatically)
export async function apiUploadFile<T>(
  endpoint: string,
  file: File
): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: buildHeaders(true),
    body: formData,
  });

  if (!response.ok) {
    const msg = await parseErrorResponse(response);
    throw new Error(msg);
  }

  return response.json() as Promise<T>;
}