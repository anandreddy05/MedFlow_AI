export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export async function uploadDocument(file: File, patientId: string, reportType: string) {
  const token = localStorage.getItem('access_token');
  const formData = new FormData();
  formData.append('file', file);
  formData.append('patient_id', patientId);
  formData.append('report_type', reportType);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    headers: {
      ...(token && { 'Authorization': `Bearer ${token}` }),
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

export async function getPendingReports() {
  return apiRequest('/reports/pending');
}

export async function approveReport(documentId: string, correctedReport: any) {
  return apiRequest('/reports/approve', {
    method: 'POST',
    body: JSON.stringify({
      document_id: documentId,
      corrected_report: correctedReport,
    }),
  });
}

export async function createPrescription(payload: any) {
  return apiRequest('/prescriptions/direct', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getPatientHistory() {
  return apiRequest('/patient/history');
}

export async function chatWithAI(query: string, history: any[] = []) {
  return apiRequest('/chat', {
    method: 'POST',
    body: JSON.stringify({ query, history }),
  });
}
