const API_BASE = import.meta.env.VITE_API_URL || '';

function authToken() {
  return localStorage.getItem('auth_token');
}

function companyHeader() {
  const company = JSON.parse(localStorage.getItem('fp_company') || 'null');
  return company ? { 'X-Company-Id': company.id } : {};
}

function authHeaders() {
  const token = authToken();
  return {
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...companyHeader(),
  };
}

async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = authToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...companyHeader(),
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

// ─── Auth ───────────────────────────────────────────────
export const authApi = {
  login: async (email, password) => {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Login failed');
    return data;
  },
  register: async (email, password, fullName) => {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Registration failed');
    return data;
  },
  verify: async (token) => {
    const response = await fetch(`${API_BASE}/auth/verify`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) return null;
    return response.json();
  },
  logout: async (token) => {
    return fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    }).catch(() => {});
  },
  me: async () => {
    const response = await fetch(`${API_BASE}/auth/me`, {
      headers: authHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch user');
    return response.json();
  },
};

// ─── Dashboard ──────────────────────────────────────────
export const getDashboardStats = (period = 'all', startDate, endDate) => {
  const params = { period };
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/dashboard/stats?${query}`);
};
export const getDashboardCharts = () => apiRequest('/dashboard/charts');
export const getAgingReport = () => apiRequest('/reports/aging');
export const globalSearch = (q) => apiRequest(`/search?q=${encodeURIComponent(q)}`);

// ─── Invoices ───────────────────────────────────────────
export const getInvoices = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/invoices${query ? '?' + query : ''}`);
};

export const getInvoicesByDateRange = (startDate, endDate, otherParams = {}) => {
  const params = { start_date: startDate, end_date: endDate, ...otherParams };
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/invoices${query ? '?' + query : ''}`);
};

export const getInvoice = (invoiceId) => apiRequest(`/invoices/${invoiceId}`);

export const uploadInvoice = async (file, invoiceType = 'supplier', projectCode = '', costCenter = '', assignedTo = '') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('invoice_type', invoiceType);
  if (projectCode) formData.append('project_code', projectCode);
  if (costCenter) formData.append('cost_center', costCenter);
  if (assignedTo) formData.append('assigned_to', assignedTo);
  return apiRequest('/invoices/upload', { method: 'POST', body: formData });
};

export const createManualInvoice = (data) =>
  apiRequest('/invoices/manual', { method: 'POST', body: JSON.stringify(data) });

export const updateInvoiceStatus = (invoiceId, status) =>
  apiRequest(`/invoices/${invoiceId}/status?status=${status}`, { method: 'PATCH' });

export const deleteInvoice = (invoiceId) =>
  apiRequest(`/invoices/${invoiceId}`, { method: 'DELETE' });

// ─── Bulk Invoice Operations ────────────────────────────
export const bulkApprove = (invoiceIds) =>
  apiRequest('/invoices/bulk/approve', { method: 'POST', body: JSON.stringify({ invoice_ids: invoiceIds }) });
export const bulkPost = (invoiceIds) =>
  apiRequest('/invoices/bulk/post', { method: 'POST', body: JSON.stringify({ invoice_ids: invoiceIds }) });
export const bulkDelete = (invoiceIds) =>
  apiRequest('/invoices/bulk/delete', { method: 'POST', body: JSON.stringify({ invoice_ids: invoiceIds }) });

// ─── Journal Entries ────────────────────────────────────
export const getJournalEntries = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/accounting/entries${query ? '?' + query : ''}`);
};

export const postJournalEntry = (entryId) =>
  apiRequest(`/accounting/entries/${entryId}/post`, { method: 'POST' });

export const reverseJournalEntry = (entryId) =>
  apiRequest(`/accounting/entries/${entryId}/reverse`, { method: 'POST' });

// ─── Chart of Accounts ──────────────────────────────────
export const getChartOfAccounts = (category = '') =>
  apiRequest(`/accounting/chart-of-accounts${category ? '?category=' + category : ''}`);

export const suggestAccount = (description, type = 'supplier') =>
  apiRequest(`/accounting/suggest-account?description=${encodeURIComponent(description)}&type=${type}`);

export const checkHealth = () => apiRequest('/health');

// ─── Admin ──────────────────────────────────────────────
export const resetAllData = () =>
  apiRequest('/admin/reset', { method: 'POST', body: JSON.stringify({ confirm: true }) });

// ─── Company Admin ──────────────────────────────────────
export const getCompanies = () => apiRequest('/auth/admin/companies');
export const createCompany = (code, name, currency = 'MUR') =>
  apiRequest('/auth/admin/companies', { method: 'POST', body: JSON.stringify({ code, name, currency }) });
export const deleteCompany = (companyId) =>
  apiRequest(`/auth/admin/companies/${companyId}`, { method: 'DELETE' });
export const getCompanyUsers = (companyId) => apiRequest(`/auth/admin/companies/${companyId}/users`);
export const assignUserToCompany = (companyId, userId) =>
  apiRequest(`/auth/admin/companies/${companyId}/users/${userId}`, { method: 'POST' });
export const removeUserFromCompany = (companyId, userId) =>
  apiRequest(`/auth/admin/companies/${companyId}/users/${userId}`, { method: 'DELETE' });
export const toggleMakerChecker = (companyId, enabled) =>
  apiRequest(`/auth/admin/companies/${companyId}/maker-checker`, { method: 'PUT', body: JSON.stringify({ enabled }) });
export const getCompanySmtp = (companyId) => apiRequest(`/auth/admin/companies/${companyId}/smtp`);
export const updateCompanySmtp = (companyId, settings) =>
  apiRequest(`/auth/admin/companies/${companyId}/smtp`, { method: 'PUT', body: JSON.stringify(settings) });

// ─── Export (blob downloads) ────────────────────────────
async function downloadBlob(endpoint, filename) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Export failed: ${response.status}`);
  }
  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

export const exportJournalEntriesExcel = (status = 'posted') =>
  downloadBlob(`/accounting/export/excel?status=${status}`, `journal_entries_${status}_${new Date().toISOString().slice(0,10)}.xlsx`);

export const exportJournalEntriesSage200 = (status = 'posted', transactionType = 'JL') =>
  downloadBlob(`/accounting/export/sage200?status=${status}&transaction_type=${transactionType}`, `Sage200_GL_Journal_${status}_${transactionType}_${new Date().toISOString().slice(0,10)}.csv`);

// ─── Document Viewer ────────────────────────────────────
export const getInvoiceDocumentUrl = (invoiceId) => {
  return `${API_BASE}/invoices/${invoiceId}/document`;
};

export const getInvoiceDocumentPreview = async (invoiceId, page = 0) => {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}/document/preview?page=${page}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error('Preview not available');
  return response.json();
};

// ─── Combined Document (invoice + supporting docs) ───────
export const getCombinedDocumentUrl = (invoiceId) => {
  return `${API_BASE}/invoices/${invoiceId}/combined-document`;
};

export const getCombinedDocumentPreview = async (invoiceId, page = 0) => {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}/combined-document/preview?page=${page}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error('Combined preview not available');
  return response.json();
};

// ─── Supporting Documents (Attachments) ──────────────────
export const listAttachments = (invoiceId) =>
  apiRequest(`/invoices/${invoiceId}/attachments`);

export const uploadAttachment = async (invoiceId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}/attachments`, {
    method: 'POST',
    headers: { ...authHeaders() },
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Upload failed');
  }
  return response.json();
};

export const deleteAttachment = (invoiceId, attachmentId) =>
  apiRequest(`/invoices/${invoiceId}/attachments/${attachmentId}`, { method: 'DELETE' });

// ─── Reclassify ─────────────────────────────────────────
export const reclassifyInvoice = async (invoiceId, userContext) => {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}/reclassify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ user_context: userContext }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Reclassification failed');
  }
  return response.json();
};

// ─── Classification Rules ───────────────────────────────
export const getClassificationRules = () => apiRequest('/accounting/classification-rules');

export const deleteClassificationRule = (ruleId) =>
  apiRequest(`/accounting/classification-rules/${ruleId}`, { method: 'DELETE' });

// ─── TDS (Tax Deducted at Source) ───────────────────────
export const getTdsRates = () => apiRequest('/tds/rates');
export const createTdsRate = (data) => apiRequest('/tds/rates', { method: 'POST', body: JSON.stringify(data) });
export const updateTdsRate = (id, data) => apiRequest(`/tds/rates/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteTdsRate = (id) => apiRequest(`/tds/rates/${id}`, { method: 'DELETE' });
export const updateInvoiceTds = (invoiceId, tdsApplicable, tdsRate) =>
  apiRequest(`/invoices/${invoiceId}/tds`, { method: 'PATCH', body: JSON.stringify({ tds_applicable: tdsApplicable, tds_rate: tdsRate }) });
export const getTdsRegister = (startDate, endDate) => {
  const params = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/tds/register${query ? '?' + query : ''}`);
};
export const markTdsRemitted = (invoiceId) =>
  apiRequest(`/tds/mark-remitted?invoice_id=${invoiceId}`, { method: 'PATCH' });

// ─── Audit Log ──────────────────────────────────────────
export const getAuditLog = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiRequest(`/audit-log${query ? '?' + query : ''}`);
};

// ─── Vendor Master ──────────────────────────────────────
export const getVendors = (search) => apiRequest(`/vendors${search ? '?search=' + search : ''}`);
export const createVendor = (data) => apiRequest('/vendors', { method: 'POST', body: JSON.stringify(data) });
export const updateVendor = (id, data) => apiRequest(`/vendors/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteVendor = (id) => apiRequest(`/vendors/${id}`, { method: 'DELETE' });
export const linkInvoiceVendor = (invoiceId, vendorId) =>
  apiRequest(`/invoices/${invoiceId}/vendor`, { method: 'PATCH', body: JSON.stringify({ vendor_id: vendorId }) });
export const unlinkInvoiceVendor = (invoiceId) =>
  apiRequest(`/invoices/${invoiceId}/vendor/unlink`, { method: 'PATCH' });

// ─── Invoice Assignment ─────────────────────────────────
export const assignInvoice = (invoiceId, userId) =>
  apiRequest(`/invoices/${invoiceId}/assign`, { method: 'PATCH', body: JSON.stringify({ assigned_to: userId }) });

// ─── Recurring Invoices ─────────────────────────────────
export const getRecurringTemplates = () => apiRequest('/recurring/templates');
export const createRecurringTemplate = (data) => apiRequest('/recurring/templates', { method: 'POST', body: JSON.stringify(data) });
export const updateRecurringTemplate = (id, data) => apiRequest(`/recurring/templates/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteRecurringTemplate = (id) => apiRequest(`/recurring/templates/${id}`, { method: 'DELETE' });
export const toggleRecurringTemplate = (id) => apiRequest(`/recurring/templates/${id}/toggle`, { method: 'PATCH' });
export const generateRecurringNow = (id) => apiRequest(`/recurring/generate-now/${id}`, { method: 'POST' });
export const toggleRecurringCompany = (companyId, enabled) =>
  apiRequest(`/auth/admin/companies/${companyId}/recurring`, { method: 'PUT', body: JSON.stringify({ enabled }) });

// ─── Exchange Rates ─────────────────────────────────────
export const getExchangeRates = () => apiRequest('/exchange-rates');
export const updateExchangeRate = (currency, rateToMur) =>
  apiRequest('/exchange-rates', { method: 'PUT', body: JSON.stringify({ currency, rate_to_mur: rateToMur }) });
export const refreshExchangeRates = () => apiRequest('/exchange-rates/refresh', { method: 'POST' });

// ─── Payment Settlement (FX) ────────────────────────────
export const settlePayment = (invoiceId, bankRate, bankCharges, paymentDate) =>
  apiRequest(`/invoices/${invoiceId}/settle-payment`, { method: 'POST', body: JSON.stringify({ bank_rate: bankRate, bank_charges: bankCharges, payment_date: paymentDate }) });
