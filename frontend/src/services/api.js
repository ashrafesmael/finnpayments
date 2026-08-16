const API_BASE = import.meta.env.VITE_API_URL || '';

function authToken() {
  return localStorage.getItem('auth_token');
}

async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = authToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (response.status === 401) {
    localStorage.removeItem('auth_token');
    if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
      window.location.href = '/login';
    }
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }
  return await response.json();
}

export const getDashboardStats = () => apiRequest('/dashboard/stats');

export const getInvoices = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/invoices${query ? '?' + query : ''}`);
};

export const getInvoice = (invoiceId) => apiRequest(`/invoices/${invoiceId}`);

export const uploadInvoice = async (file, invoiceType = 'supplier', projectCode = '', costCenter = '') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('invoice_type', invoiceType);
  if (projectCode) formData.append('project_code', projectCode);
  if (costCenter) formData.append('cost_center', costCenter);
  return apiRequest('/invoices/upload', { method: 'POST', body: formData });
};

export const createManualInvoice = (data) =>
  apiRequest('/invoices/manual', { method: 'POST', body: JSON.stringify(data) });

export const updateInvoiceStatus = (invoiceId, status) =>
  apiRequest(`/invoices/${invoiceId}/status?status=${status}`, { method: 'PATCH' });

export const deleteInvoice = (invoiceId) =>
  apiRequest(`/invoices/${invoiceId}`, { method: 'DELETE' });

export const getJournalEntries = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/accounting/entries${query ? '?' + query : ''}`);
};

export const postJournalEntry = (entryId) =>
  apiRequest(`/accounting/entries/${entryId}/post`, { method: 'POST' });

export const reverseJournalEntry = (entryId) =>
  apiRequest(`/accounting/entries/${entryId}/reverse`, { method: 'POST' });

export const getChartOfAccounts = (category = '') =>
  apiRequest(`/accounting/chart-of-accounts${category ? '?category=' + category : ''}`);

export const suggestAccount = (description, type = 'supplier') =>
  apiRequest(`/accounting/suggest-account?description=${encodeURIComponent(description)}&type=${type}`);

export const checkHealth = () => apiRequest('/health');

// ─── Admin ───────────────────────────────────────────────
export const resetAllData = () =>
  apiRequest('/admin/reset', { method: 'POST', body: JSON.stringify({ confirm: true }) });

// ─── Export ──────────────────────────────────────────────
export const exportJournalEntriesExcel = async (status = 'posted') => {
  const API_BASE2 = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const url = `${API_BASE2}/accounting/export/excel?status=${status}`;
  const response = await fetch(url);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Export failed: ${response.status}`);
  }
  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `journal_entries_${status}_${new Date().toISOString().slice(0,10)}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
};

// ─── Document Viewer ─────────────────────────────────────
export const getInvoiceDocumentUrl = (invoiceId) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  return `${base}/invoices/${invoiceId}/document`;
};


// ─── Document Preview ────────────────────────────────────
export const getInvoiceDocumentPreview = async (invoiceId, page = 0) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const response = await fetch(`${base}/invoices/${invoiceId}/document/preview?page=${page}`);
  if (!response.ok) throw new Error('Preview not available');
  return response.json();
};


// ─── Reclassify ──────────────────────────────────────────
export const reclassifyInvoice = async (invoiceId, userContext) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const response = await fetch(`${base}/invoices/${invoiceId}/reclassify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_context: userContext }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Reclassification failed');
  }
  return response.json();
};


// ─── Classification Rules ────────────────────────────────
export const getClassificationRules = async () => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const response = await fetch(`${base}/accounting/classification-rules`);
  if (!response.ok) throw new Error('Failed to fetch rules');
  return response.json();
};

export const deleteClassificationRule = async (ruleId) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const response = await fetch(`${base}/accounting/classification-rules/${ruleId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete rule');
  return response.json();
};
