import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import {
  getDashboardStats, getInvoices, getInvoice, uploadInvoice,
  updateInvoiceStatus, deleteInvoice, getJournalEntries,
  postJournalEntry, reverseJournalEntry, getChartOfAccounts, checkHealth,
  exportJournalEntriesExcel,
  exportJournalEntriesSage200,
  updateInvoiceTds, markTdsRemitted, getTdsRates, createTdsRate, updateTdsRate, deleteTdsRate, getTdsRegister,
  getAuditLog,
  getVendors, createVendor, updateVendor, deleteVendor, linkInvoiceVendor, unlinkInvoiceVendor,
  assignInvoice,
  getRecurringTemplates, createRecurringTemplate, updateRecurringTemplate, deleteRecurringTemplate, toggleRecurringTemplate, generateRecurringNow, toggleRecurringCompany,
  getExchangeRates, updateExchangeRate, refreshExchangeRates, settlePayment,
  getInvoiceDocumentUrl,
  getInvoiceDocumentPreview,
  reclassifyInvoice,
  getClassificationRules, deleteClassificationRule, resetAllData
} from './services/api.js';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import AdminPanel from './pages/AdminPanel';

/* ─── Icons (inline SVG) ────────────────────────────── */
const Icons = {
  Dashboard: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  DocView: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,
  Download: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>,
  Brain: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 2a7 7 0 017 7c0 2.5-1.5 4-3 5s-2 2-2 4h-4c0-2-0.5-3-2-4S5 11.5 5 9a7 7 0 017-7z"/><line x1="10" y1="21" x2="14" y2="21"/></svg>,
  Upload: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
  FileText: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,
  Book: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>,
  List: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3" cy="6" r="1" fill="currentColor"/><circle cx="3" cy="12" r="1" fill="currentColor"/><circle cx="3" cy="18" r="1" fill="currentColor"/></svg>,
  Check: () => <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polyline points="20,6 9,17 4,12"/></svg>,
  X: () => <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  ArrowLeft: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12,19 5,12 12,5"/></svg>,
  Trash: () => <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>,
  Dollar: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>,
  TrendUp: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/><polyline points="17,6 23,6 23,12"/></svg>,
  Clock: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/></svg>,
  Alert: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  Sun: () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
  Moon: () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>,
  Refresh: () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><polyline points="23,4 23,10 17,10"/><polyline points="1,20 1,14 7,14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>,
  Users: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>,
  LogOut: () => <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16,17 21,12 16,7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
};

/* ─── Helpers ────────────────────────────────────────── */
const fmtCurrency = (amt, cur = 'MUR') => {
  if (amt == null) return '-';
  const sym = { MUR: 'Rs', USD: '$', EUR: '€', GBP: '£', ZAR: 'R' }[cur] || cur;
  return `${sym} ${Number(amt).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const StatusBadge = ({ status }) => (
  <span className={`badge badge-${status || 'draft'}`}>{(status || '').replace('_', ' ')}</span>
);

const Loading = () => (
  <div className="loading-container"><div className="spinner" /><span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading...</span></div>
);

const Empty = ({ text }) => <div className="empty-state">{text || 'No data found'}</div>;

/* ═══════════════════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════════════════ */
function Sidebar({ active, onNavigate, health, theme, onToggleTheme, onReset, resetting, user, onLogout, isAdmin, companies, selectedCompany, onSelectCompany }) {
  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: Icons.Dashboard },
    { id: 'upload', label: 'Upload Invoice', icon: Icons.Upload },
    { id: 'invoices', label: 'Invoices', icon: Icons.FileText },
    { id: 'entries', label: 'Journal Entries', icon: Icons.Book },
    { id: 'accounts', label: 'Chart of Accounts', icon: Icons.List },
    { id: 'vendors', label: 'Vendors', icon: Icons.Users },
    { id: 'recurring', label: 'Recurring', icon: Icons.Refresh },
    { id: 'fxrates', label: 'Exchange Rates', icon: Icons.Dollar },
    { id: 'rules', label: 'Learned Rules', icon: Icons.Brain },
    { id: 'tds', label: 'TDS Register', icon: Icons.Dollar },
    ...(isAdmin ? [{ id: 'audit', label: 'Audit Log', icon: Icons.List }] : []),
    ...(isAdmin ? [{ id: 'admin', label: 'User Management', icon: Icons.Users }] : []),
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">fp</div>
        <div className="sidebar-logo-text">
          <h1>finnpayments</h1>
          <p>Invoice Processing & Accounting</p>
        </div>
      </div>
      {companies && companies.length > 0 && (
        <div className="sidebar-company-selector">
          <label>Active Company</label>
          <select
            className="company-select"
            value={selectedCompany?.id || ''}
            onChange={(e) => {
              const company = companies.find(c => c.id === e.target.value);
              if (company) onSelectCompany(company);
            }}
          >
            {companies.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      )}
      <nav className="sidebar-nav">
        {items.map(({ id, label, icon: Icon }) => (
          <button key={id} className={`sidebar-nav-item ${active === id ? 'active' : ''}`} onClick={() => onNavigate(id)}>
            <Icon />{label}
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        <button className="sidebar-footer-btn" onClick={onToggleTheme} title="Switch theme">
          {theme === 'dark' ? <Icons.Sun /> : <Icons.Moon />}
          {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
        </button>
        {isAdmin && (
          <button className="sidebar-footer-btn danger" onClick={onReset} disabled={resetting} title="Delete all invoices and journal entries for the active company">
            <span className={resetting ? 'spinning' : ''} style={{ display: 'flex' }}><Icons.Refresh /></span>
            {resetting ? 'Resetting…' : 'Reset Data'}
          </button>
        )}
      </div>
      <div className="sidebar-status">
        <div className={`status-dot ${health ? 'online' : 'offline'}`} />
        API {health ? 'Connected' : 'Offline'}
      </div>
      {user && (
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">{user.full_name?.charAt(0)?.toUpperCase() || 'U'}</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user.full_name}</div>
            <div className="sidebar-user-role">{user.role}</div>
          </div>
          <button className="sidebar-logout" onClick={onLogout} title="Sign out"><Icons.LogOut /></button>
        </div>
      )}
    </aside>
  );
}

/* ═══════════════════════════════════════════════════════
   DASHBOARD
   ═══════════════════════════════════════════════════════ */
function Dashboard({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [showCustom, setShowCustom] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const sd = period === 'custom' ? customStart : undefined;
      const ed = period === 'custom' ? customEnd : undefined;
      const r = await getDashboardStats(period, sd, ed);
      setStats(r);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [period, customStart, customEnd]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Loading />;
  if (!stats) return <Empty text="Failed to load dashboard" />;

  const periods = [
    { id: 'all', label: 'All Time' },
    { id: 'month', label: 'This Month' },
    { id: 'last_month', label: 'Last Month' },
    { id: 'quarter', label: 'This Quarter' },
    { id: 'year', label: 'This Year' },
    { id: 'custom', label: 'Custom' },
  ];

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Dashboard</h2>
        <button className="btn btn-primary" onClick={() => onNavigate('upload')}>Upload Invoice</button>
      </div>

      <div className="filter-bar">
        {periods.map(p => (
          <button key={p.id} className={`filter-pill ${period === p.id ? 'active' : ''}`} onClick={() => { setPeriod(p.id); setShowCustom(p.id === 'custom'); }}>
            {p.label}
          </button>
        ))}
      </div>
      {showCustom && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
          <input type="date" className="input" style={{ width: 160 }} value={customStart} onChange={(e) => setCustomStart(e.target.value)} />
          <span className="text-muted">to</span>
          <input type="date" className="input" style={{ width: 160 }} value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} />
          <button className="btn btn-sm btn-primary" onClick={load} disabled={!customStart || !customEnd}>Apply</button>
        </div>
      )}

      <div className="stats-grid">
        {[
          { label: 'Total Invoices', value: stats.total_invoices, Icon: Icons.FileText, color: '' },
          { label: 'Pending Review', value: stats.pending_review, Icon: Icons.Clock, color: 'amber' },
          { label: 'Total Payable', value: fmtCurrency(stats.total_payable), Icon: Icons.Dollar, color: 'red' },
          { label: 'Total Receivable', value: fmtCurrency(stats.total_receivable), Icon: Icons.TrendUp, color: 'accent' },
        ].map((c, i) => (
          <div key={i} className="stat-card animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
            <div className="stat-card-header">
              <span className="stat-card-label">{c.label}</span>
              <span className={`stat-card-icon ${c.color}`}><c.Icon /></span>
            </div>
            <div className={`stat-card-value ${c.color}`}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Recent Invoices {stats.start_date ? `(${stats.start_date} to ${stats.end_date})` : ''}</h3>
          <button className="link-btn" onClick={() => onNavigate('invoices')}>View All →</button>
        </div>
        <table className="data-table">
          <thead><tr><th>Invoice</th><th>Vendor</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {(stats.recent_invoices || []).slice(0, 8).map((inv, i) => (
              <tr key={i} onClick={() => onNavigate('detail', inv.invoice_id)}>
                <td className="mono text-xs text-accent">{inv.invoice_number || inv.invoice_id}</td>
                <td>{inv.vendor_name}</td>
                <td className="mono text-sm">{fmtCurrency(inv.total_amount, inv.currency)}</td>
                <td><StatusBadge status={inv.status} /></td>
                <td className="text-muted text-xs">{inv.invoice_date || '-'}</td>
              </tr>
            ))}
            {(!stats.recent_invoices || stats.recent_invoices.length === 0) && (
              <tr><td colSpan={5}><Empty text="No invoices in this period." /></td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   INVOICE UPLOAD
   ═══════════════════════════════════════════════════════ */
function InvoiceUpload({ onNavigate }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [invoiceType, setInvoiceType] = useState('supplier');
  const [projectCode, setProjectCode] = useState('');
  const [costCenter, setCostCenter] = useState('');
  const [assignedTo, setAssignedTo] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [companyUsers, setCompanyUsers] = useState([]);
  const ref = useRef(null);
  const { user } = useAuth();

  useEffect(() => {
    const API_URL = import.meta.env.VITE_API_URL || '';
    const token = localStorage.getItem('auth_token');
    fetch(`${API_URL}/auth/company-users`, { headers: { 'Authorization': 'Bearer ' + token } })
      .then(r => r.ok ? r.json() : [])
      .then(users => setCompanyUsers(users.filter(u => u.status === 'approved')))
      .catch(() => {});
  }, []);

  const handleDrop = useCallback((e) => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setError(null);
    try { setResult(await uploadInvoice(file, invoiceType, projectCode, costCenter, assignedTo)); }
    catch (err) { setError(err.message); }
    finally { setUploading(false); }
  };

  if (result && result.multi_invoice) return <MultiInvoiceResult result={result} onNavigate={onNavigate} onReset={() => { setResult(null); setFile(null); }} />;
  if (result) return <UploadResult result={result} onNavigate={onNavigate} onReset={() => { setResult(null); setFile(null); }} />;

  return (
    <div className="animate-fade-in space-y max-w-3xl">
      <div className="page-header"><h2>Upload Invoice</h2></div>

      <div className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => ref.current?.click()}>
        <input ref={ref} type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.csv,.xlsx,.xls,.docx,.txt"
          onChange={(e) => setFile(e.target.files[0])} />
        <div className="upload-zone-icon"><Icons.Upload /></div>
        {file ? (
          <>
            <div className="upload-zone-file">{file.name}</div>
            <div className="upload-zone-size">{(file.size / 1024).toFixed(1)} KB</div>
          </>
        ) : (
          <>
            <div className="upload-zone-text">Drop invoice file here or click to browse</div>
            <div className="upload-zone-hint">PDF, Image, CSV, Excel supported</div>
          </>
        )}
      </div>

      <div className="form-grid">
        <div>
          <label className="input-label">Invoice Type</label>
          <select className="input" value={invoiceType} onChange={(e) => setInvoiceType(e.target.value)}>
            <option value="supplier">Supplier (AP)</option>
            <option value="client">Client (AR)</option>
            <option value="credit_note">Credit Note</option>
            <option value="debit_note">Debit Note</option>
          </select>
        </div>
        <div>
          <label className="input-label">Project Code</label>
          <input className="input" value={projectCode} onChange={(e) => setProjectCode(e.target.value)} placeholder="e.g. SIG-001" />
        </div>
        <div>
          <label className="input-label">Cost Center</label>
          <input className="input" value={costCenter} onChange={(e) => setCostCenter(e.target.value)} placeholder="e.g. ADMIN" />
        </div>
      </div>

      <div className="form-grid" style={{ gridTemplateColumns: '1fr' }}>
        <div>
          <label className="input-label">Assign To (for approval)</label>
          <select className="input" value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)}>
            <option value="">Myself (default)</option>
            {companyUsers.filter(u => u.id !== user?.id).map(u => (
              <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
            ))}
          </select>
        </div>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <button className="btn btn-primary" onClick={handleUpload} disabled={!file || uploading}>
        {uploading ? 'Processing...' : 'Process Invoice'}
      </button>
    </div>
  );
}

/* ─── Upload Result ──────────────────────────────────── */
function MultiInvoiceResult({ result, onNavigate, onReset }) {
  const invoices = result.invoices || [];
  return (
    <div className="animate-fade-in space-y">
      <div className="page-header-back">
        <button className="back-btn" onClick={onReset}><Icons.ArrowLeft /></button>
        <h2 style={{ fontSize: 24, fontWeight: 600, color: 'var(--text-white)' }}>Multi-Invoice Upload</h2>
      </div>
      <div className="success-banner">
        <div>
          <div className="success-banner-text">{result.message}</div>
          <div className="success-banner-sub">{result.count} invoices detected in uploaded PDF</div>
        </div>
      </div>
      <div className="card">
        <div className="card-header"><h3>Invoices Processed</h3></div>
        <table className="data-table">
          <thead><tr><th>#</th><th>Vendor</th><th>Invoice #</th><th>Date</th><th>Total</th><th>Action</th></tr></thead>
          <tbody>{invoices.map((inv, i) => {
            const d = inv.extracted_data || {};
            return (
              <tr key={i}>
                <td className="text-muted">{i + 1}</td>
                <td style={{ fontWeight: 500, color: 'var(--text-white)' }}>{d.vendor_name || 'Unknown'}</td>
                <td className="mono text-sm">{d.invoice_number || '-'}</td>
                <td className="text-muted text-sm">{d.invoice_date || '-'}</td>
                <td className="mono" style={{ color: 'var(--accent)', fontWeight: 600 }}>{fmtCurrency(d.total_amount, d.currency)}</td>
                <td><button className="btn btn-sm" onClick={() => onNavigate('detail', inv.invoice_id)}>View</button></td>
              </tr>
            );
          })}</tbody>
        </table>
      </div>
      <div style={{ display: 'flex', gap: 12 }}>
        <button className="btn btn-primary" onClick={() => onNavigate('invoices')}>View All Invoices</button>
        <button className="btn" onClick={onReset}>Upload More</button>
      </div>
    </div>
  );
}

function UploadResult({ result, onNavigate, onReset }) {
  const d = result.extracted_data || {};
  const entries = result.suggested_entries || [];

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header-back">
        <button className="back-btn" onClick={onReset}><Icons.ArrowLeft /></button>
        <h2 style={{ fontSize: 24, fontWeight: 600, color: 'var(--text-white)' }}>Processing Result</h2>
      </div>

      <div className="success-banner">
        <div>
          <div className="success-banner-text">{result.message}</div>
          <div className="success-banner-sub">Invoice ID: <span className="mono">{result.invoice_id}</span></div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="confidence-label">Confidence</div>
          <div className="confidence-value">{((d.confidence_score || 0) * 100).toFixed(0)}%</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><h3>Extracted Data</h3></div>
        <div style={{ padding: 20 }}>
          <div className="detail-grid">
            <div>
              {[['Vendor', d.vendor_name], ['Invoice #', d.invoice_number], ['Date', d.invoice_date], ['Due Date', d.due_date], ['BRN', d.vendor_brn]].map(([l, v], i) => (
                <div key={i} className="detail-row"><span className="detail-label">{l}</span><span className="detail-value">{v || '-'}</span></div>
              ))}
            </div>
            <div>
              {[['Currency', d.currency], ['Subtotal', fmtCurrency(d.subtotal, d.currency)], ['VAT', fmtCurrency(d.tax_total, d.currency)]].map(([l, v], i) => (
                <div key={i} className="detail-row"><span className="detail-label">{l}</span><span className="detail-value">{v || '-'}</span></div>
              ))}
              <div className="detail-total">
                <span className="detail-total-label">Total</span>
                <span className="detail-total-value">{fmtCurrency(d.total_amount, d.currency)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Line Items */}
      {(d.line_items || []).length > 0 && (
        <div className="card">
          <div className="card-header"><h3>Line Items</h3></div>
          <table className="data-table">
            <thead><tr><th>#</th><th>Description</th><th>Qty</th><th>Price</th><th>Amount</th><th>Tax</th></tr></thead>
            <tbody>{d.line_items.map((it, i) => (
              <tr key={i}>
                <td className="text-muted">{it.line_number || i + 1}</td>
                <td>{it.description}</td>
                <td className="mono text-sm">{it.quantity}</td>
                <td className="mono text-sm">{fmtCurrency(it.unit_price, d.currency)}</td>
                <td className="mono text-sm">{fmtCurrency(it.amount, d.currency)}</td>
                <td className="text-muted text-sm">{it.tax_rate}%</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {/* Journal Entries */}
      {entries.length > 0 && (
        <div className="card">
          <div className="card-header"><h3>Suggested Accounting Entries</h3></div>
          {entries.map((entry, ei) => (
            <div key={ei} className="je-block">
              <div className="je-header">
                <div><span className="je-ref">{entry.entry_id}</span><span className="je-desc"> — {entry.description}</span></div>
                {entry.is_balanced && <span className="je-balanced"><Icons.Check /> Balanced</span>}
              </div>
              <table className="data-table">
                <thead><tr><th>Account</th><th>Description</th><th className="text-right">Debit</th><th className="text-right">Credit</th></tr></thead>
                <tbody>
                  {(entry.lines || []).map((l, li) => (
                    <tr key={li}>
                      <td><span className="mono text-xs text-accent">{l.account_code}</span> <span className="text-muted text-xs">{l.account_name}</span></td>
                      <td className="text-xs">{l.description}</td>
                      <td className="text-right debit">{l.debit > 0 ? fmtCurrency(l.debit, d.currency) : ''}</td>
                      <td className="text-right credit">{l.credit > 0 ? fmtCurrency(l.credit, d.currency) : ''}</td>
                    </tr>
                  ))}
                  <tr className="je-totals-row">
                    <td colSpan={2} style={{ textAlign: 'right', fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Totals</td>
                    <td className="text-right debit">{fmtCurrency(entry.total_debit, d.currency)}</td>
                    <td className="text-right credit">{fmtCurrency(entry.total_credit, d.currency)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      <div className="btn-group">
        <button className="btn btn-primary" onClick={() => onNavigate('detail', result.invoice_id)}>View Invoice</button>
        <button className="btn btn-secondary" onClick={onReset}>Upload Another</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   INVOICE LIST
   ═══════════════════════════════════════════════════════ */
function InvoiceList({ onNavigate }) {
  const [invoices, setInvoices] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filter) params.status = filter;
      if (search) params.search = search;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const r = await getInvoices(params);
      setInvoices(r.invoices || []); setTotal(r.total || 0);
    }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filter, search, startDate, endDate]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Invoices <span className="count">({total})</span></h2>
        <button className="btn btn-primary" onClick={() => onNavigate('upload')}>+ Upload</button>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="input" style={{ width: 260 }} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search vendor or invoice #..." />
        <input type="date" className="input" style={{ width: 150 }} value={startDate} onChange={(e) => setStartDate(e.target.value)} title="From date" />
        <span className="text-muted text-xs">to</span>
        <input type="date" className="input" style={{ width: 150 }} value={endDate} onChange={(e) => setEndDate(e.target.value)} title="To date" />
        {(startDate || endDate) && <button className="btn btn-sm" onClick={() => { setStartDate(''); setEndDate(''); }}>Clear dates</button>}
        <div className="filter-bar">
          {['', 'pending_review', 'approved', 'posted', 'paid', 'rejected'].map(s => (
            <button key={s} className={`filter-pill ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
              {s ? s.replace('_', ' ') : 'All'}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        {loading ? <Loading /> : (
          <table className="data-table">
            <thead><tr><th>Invoice #</th><th>Vendor</th><th>Type</th><th>Amount</th><th>Status</th><th>Date</th><th></th></tr></thead>
            <tbody>
              {invoices.map(inv => (
                <tr key={inv.invoice_id} onClick={() => onNavigate('detail', inv.invoice_id)}>
                  <td className="mono text-xs text-accent">{inv.invoice_number || inv.invoice_id?.slice(-10)}</td>
                  <td>{inv.vendor_name}</td>
                  <td className="text-xs text-muted">{inv.invoice_type}</td>
                  <td className="mono text-sm">{fmtCurrency(inv.total_amount, inv.currency)}</td>
                  <td><StatusBadge status={inv.status} /></td>
                  <td className="text-xs text-muted">{inv.invoice_date}</td>
                  <td><button className="delete-btn" onClick={(e) => { e.stopPropagation(); if (confirm('Delete this invoice?')) deleteInvoice(inv.invoice_id).then(() => load()).catch(err => alert(err.message || 'Cannot delete posted/paid invoices')); }}><Icons.Trash /></button></td>
                </tr>
              ))}
              {invoices.length === 0 && <tr><td colSpan={7}><Empty text="No invoices found" /></td></tr>}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   INVOICE DETAIL
   ═══════════════════════════════════════════════════════ */


function ReclassifyBanner({ invoiceId, lineItems, onReclassified }) {
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const defaultItems = (lineItems || []).filter(li => li.account_code === '01-6000-04');
  if (defaultItems.length === 0 && !result) return null;

  const handleSubmit = async () => {
    if (!context.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await reclassifyInvoice(invoiceId, context);
      setResult(res);
      setTimeout(() => onReclassified(), 1500);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="card" style={{ borderColor: '#27ae60', borderWidth: 1, borderStyle: 'solid' }}>
        <div style={{ padding: 16 }}>
          <div style={{ color: '#27ae60', fontWeight: 600, marginBottom: 8 }}>✓ {result.message}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>📚 Learned for future invoices from this vendor</div>
          {(result.updates || []).map((u, i) => (
            <div key={i} style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>
              Line {u.line_number}: <span className="mono" style={{ color: '#e74c3c', textDecoration: 'line-through' }}>{u.old_account}</span> → <span className="mono" style={{ color: '#27ae60' }}>{u.new_account}</span> {u.account_name} <span style={{ fontSize: 11, fontStyle: 'italic' }}>({u.reason})</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ borderColor: '#f39c12', borderWidth: 1, borderStyle: 'solid' }}>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 18 }}>⚠️</span>
          <span style={{ fontWeight: 600, color: '#f39c12' }}>Account classification needs your input</span>
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
          {defaultItems.length} line item{defaultItems.length > 1 ? 's were' : ' was'} assigned to a default account (Licences).
          Describe the nature of this expense so the system can assign the correct GL account:
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={context}
            onChange={e => setContext(e.target.value)}
            placeholder="e.g. Security guard services for shopping mall, IT hosting fees, golf course fertilizer delivery..."
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 6,
              border: '1px solid var(--border)', background: 'var(--bg-card)',
              color: 'var(--text-white)', fontSize: 13,
            }}
            onKeyDown={e => { if (e.key === 'Enter' && !loading) handleSubmit(); }}
          />
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading || !context.trim()}
            style={{ whiteSpace: 'nowrap' }}
          >
            {loading ? 'Classifying...' : 'Reclassify'}
          </button>
        </div>
        {error && <div style={{ color: '#e74c3c', fontSize: 12, marginTop: 8 }}>{error}</div>}
      </div>
    </div>
  );
}

function DocumentPreview({ invoiceId }) {
  const [preview, setPreview] = useState(null);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadPage = useCallback(async (p) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getInvoiceDocumentPreview(invoiceId, p);
      setPreview(data);
      setPage(data.current_page);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [invoiceId]);

  useEffect(() => { loadPage(0); }, [loadPage]);

  return (
    <div className="card">
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Source Document</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {preview && preview.total_pages > 1 && (
            <>
              <button className="btn btn-sm" disabled={page <= 0} onClick={() => loadPage(page - 1)}>← Prev</button>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Page {page + 1} of {preview.total_pages}</span>
              <button className="btn btn-sm" disabled={page >= preview.total_pages - 1} onClick={() => loadPage(page + 1)}>Next →</button>
            </>
          )}
          <a href={getInvoiceDocumentUrl(invoiceId)} download className="btn btn-sm">Download</a>
        </div>
      </div>
      <div style={{ padding: 16, background: '#f5f5f0', minHeight: 200, display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '0 0 8px 8px' }}>
        {loading && <div style={{ color: '#666' }}>Loading preview...</div>}
        {error && <div style={{ color: '#c00' }}>Preview not available</div>}
        {!loading && !error && preview && (
          <img
            src={`data:${preview.mime_type};base64,${preview.image}`}
            alt={`Invoice page ${page + 1}`}
            style={{ maxWidth: '100%', maxHeight: 800, boxShadow: '0 2px 12px rgba(0,0,0,0.15)', borderRadius: 4 }}
          />
        )}
      </div>
    </div>
  );
}

function TdsOverride({ invoice, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [applicable, setApplicable] = useState(invoice.tds_applicable || false);
  const [rate, setRate] = useState(invoice.tds_rate || 0);

  if (!editing) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 13, color: 'var(--text-muted)' }}>
        <span>TDS: {invoice.tds_applicable ? `Yes (${invoice.tds_rate}%)` : 'Not applicable'}</span>
        <button className="btn btn-sm" onClick={() => { setApplicable(invoice.tds_applicable || false); setRate(invoice.tds_rate || 0); setEditing(true); }}>Override TDS</button>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 16, borderColor: 'var(--border)', borderWidth: 1, borderStyle: 'solid' }}>
      <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>TDS Override</div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <input type="checkbox" checked={applicable} onChange={(e) => setApplicable(e.target.checked)} />
          TDS Applicable
        </label>
        {applicable && (
          <input
            type="number" step="0.1" className="input" style={{ width: 80 }}
            value={rate} onChange={(e) => setRate(parseFloat(e.target.value) || 0)}
            placeholder="Rate %"
          />
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary btn-sm" onClick={() => { onUpdate(applicable, rate); setEditing(false); }}>Save</button>
          <button className="btn btn-sm" onClick={() => setEditing(false)}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

function AssigneeDropdown({ currentAssignee, onAssign }) {
  const [users, setUsers] = useState([]);
  const [show, setShow] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    const API_URL = import.meta.env.VITE_API_URL || '';
    const token = localStorage.getItem('auth_token');
    fetch(`${API_URL}/auth/company-users`, { headers: { 'Authorization': 'Bearer ' + token } })
      .then(r => r.ok ? r.json() : [])
      .then(u => setUsers(u.filter(x => x.status === 'approved')))
      .catch(() => {});
  }, []);

  const assignee = users.find(u => u.id === currentAssignee);

  if (!show) {
    return (
      <>
        <span className="text-sm">{assignee ? assignee.full_name : currentAssignee === user?.id ? 'You' : 'Unassigned'}</span>
        <button className="btn btn-sm" onClick={() => setShow(true)}>Reassign</button>
      </>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 4 }}>
      <select className="input" style={{ width: 200, fontSize: 13 }} defaultValue={currentAssignee || ''} onChange={(e) => { if (e.target.value) { onAssign(e.target.value); setShow(false); } }}>
        <option value="">Select user...</option>
        {users.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
      </select>
      <button className="btn btn-sm" onClick={() => setShow(false)}>Cancel</button>
    </div>
  );
}

function PaymentSettlementForm({ inv, onSettle, onCancel }) {
  const [bankRate, setBankRate] = useState(inv.exchange_rate || 1.0);
  const [bankCharges, setBankCharges] = useState(0);
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10));

  const bookedBase = (inv.total_amount * (inv.exchange_rate || 1.0)).toFixed(2);
  const actualBase = (inv.total_amount * (parseFloat(bankRate) || 0)).toFixed(2);
  const fxDiff = (actualBase - bookedBase).toFixed(2);
  const totalBank = (parseFloat(actualBase) + parseFloat(bankCharges || 0)).toFixed(2);

  return (
    <div className="card" style={{ padding: 20, borderColor: 'var(--accent)', borderWidth: 1, borderStyle: 'solid' }}>
      <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 16 }}>Settle Payment (Foreign Currency)</h3>
      <div className="detail-grid">
        <div className="detail-row"><span className="detail-label">Invoice Amount</span><span className="detail-value">{fmtCurrency(inv.total_amount, inv.currency)}</span></div>
        <div className="detail-row"><span className="detail-label">Booked Rate</span><span className="detail-value">{inv.exchange_rate || 1.0}</span></div>
        <div className="detail-row"><span className="detail-label">Booked in MUR</span><span className="detail-value">{fmtCurrency(bookedBase)}</span></div>
        <div className="detail-row"><span className="detail-label">Bank Rate</span><span className="detail-value"><input type="number" step="0.0001" className="input" style={{ width: 100 }} value={bankRate} onChange={(e) => setBankRate(e.target.value)} /></span></div>
        <div className="detail-row"><span className="detail-label">Bank Charges (MUR)</span><span className="detail-value"><input type="number" step="0.01" className="input" style={{ width: 100 }} value={bankCharges} onChange={(e) => setBankCharges(e.target.value)} /></span></div>
        <div className="detail-row"><span className="detail-label">Payment Date</span><span className="detail-value"><input type="date" className="input" style={{ width: 130 }} value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} /></span></div>
      </div>
      <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-surface-2)', borderRadius: 8 }}>
        <div className="detail-row"><span className="detail-label">Amount at bank rate</span><span className="detail-value mono">{fmtCurrency(actualBase)}</span></div>
        <div className="detail-row"><span className="detail-label">Bank charges</span><span className="detail-value mono">{fmtCurrency(bankCharges || 0)}</span></div>
        <div className="detail-row"><span className="detail-label">Total bank debit</span><span className="detail-value mono" style={{ fontWeight: 600 }}>{fmtCurrency(totalBank)}</span></div>
        <div className="detail-row">
          <span className="detail-label">FX {fxDiff > 0 ? 'Loss' : (fxDiff < 0 ? 'Gain' : 'None')}</span>
          <span className="detail-value mono" style={{ color: fxDiff > 0 ? 'var(--red)' : fxDiff < 0 ? 'var(--accent)' : 'var(--text-muted)' }}>
            {fxDiff != 0 ? fmtCurrency(Math.abs(fxDiff)) : '-'}
          </span>
        </div>
      </div>
      <div className="btn-group" style={{ marginTop: 16 }}>
        <button className="btn btn-green" onClick={() => onSettle(parseFloat(bankRate) || 0, parseFloat(bankCharges) || 0, paymentDate)}>Settle Payment</button>
        <button className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function VendorLinkDropdown({ invoiceId, onLinked }) {
  const [vendors, setVendors] = useState([]);
  const [show, setShow] = useState(false);

  useEffect(() => { getVendors().then(r => setVendors(r.vendors || [])).catch(() => {}); }, []);

  const handleLink = async (vendorId, vendorName) => {
    try { await linkInvoiceVendor(invoiceId, vendorId); setShow(false); onLinked(); }
    catch (e) { alert(e.message); }
  };

  if (!show) {
    return <button className="btn btn-sm" onClick={() => setShow(true)}>Link Vendor</button>;
  }

  return (
    <div style={{ position: 'relative' }}>
      <select className="input" style={{ width: 200, fontSize: 13 }} onChange={(e) => { if (e.target.value) handleLink(parseInt(e.target.value)); }} defaultValue="">
        <option value="">Select vendor...</option>
        {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
      </select>
      <button className="btn btn-sm" style={{ marginLeft: 4 }} onClick={() => setShow(false)}>Cancel</button>
    </div>
  );
}

function InvoiceDetail({ invoiceId, onNavigate }) {
  const [inv, setInv] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const { user, selectedCompany } = useAuth();

  useEffect(() => { getInvoice(invoiceId).then(setInv).catch(console.error).finally(() => setLoading(false)); }, [invoiceId]);

  const changeStatus = async (s) => { try { await updateInvoiceStatus(invoiceId, s); setInv(await getInvoice(invoiceId)); } catch (e) { alert(e.message); } };

  if (loading) return <Loading />;
  if (!inv) return <Empty text="Invoice not found" />;

  const makerCheckerOn = selectedCompany?.maker_checker_enabled;
  const canPost = !makerCheckerOn || !inv.approved_by || inv.approved_by !== user?.id;

  return (
    <div className="animate-fade-in space-y">
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24 }}>
        <button className="back-btn" onClick={() => onNavigate('invoices')}><Icons.ArrowLeft /></button>
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-white)' }}>{inv.vendor_name}</h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Invoice {inv.invoice_number} · <span className="mono">{inv.invoice_id}</span></p>
        </div>
        <StatusBadge status={inv.status} />
      </div>

      <div className="btn-group">
        {inv.status === 'pending_review' && (<>
          <button className="btn btn-blue" onClick={() => changeStatus('approved')}><Icons.Check /> Approve</button>
          <button className="btn btn-danger" onClick={() => changeStatus('rejected')}><Icons.X /> Reject</button>
        </>)}
        {inv.status === 'approved' && (
          <button className="btn btn-primary" onClick={() => changeStatus('posted')} disabled={!canPost} title={!canPost ? 'Maker/checker: another user must post this invoice' : ''}>
            Post to GL
          </button>
        )}
        {inv.status === 'posted' && (
          inv.currency && inv.currency.toUpperCase() !== 'MUR' ? (
            <button className="btn btn-green" onClick={() => setShowPaymentForm(true)}>Settle Payment</button>
          ) : (
            <button className="btn btn-green" onClick={() => changeStatus('paid')}>Mark as Paid</button>
          )
        )}
      </div>
      {showPaymentForm && inv.currency && inv.currency.toUpperCase() !== 'MUR' && (
        <PaymentSettlementForm
          inv={inv}
          onSettle={async (bankRate, bankCharges, paymentDate) => {
            try {
              await settlePayment(inv.invoice_id, bankRate, bankCharges, paymentDate);
              setShowPaymentForm(false);
              setInv(await getInvoice(invoiceId));
            } catch (e) { alert(e.message); }
          }}
          onCancel={() => setShowPaymentForm(false)}
        />
      )}
      {makerCheckerOn && inv.status === 'approved' && !canPost && (
        <div className="alert-info" style={{ fontSize: 13, padding: '10px 14px', borderRadius: 6, background: 'var(--amber-muted)', border: '1px solid var(--amber)', color: 'var(--amber)' }}>
          Maker/checker is enabled. You approved this invoice, so another user must post it to the GL.
        </div>
      )}
      {makerCheckerOn && (inv.approved_by || inv.posted_by) && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
          {inv.approved_by && inv.approved_by === user?.id && 'You approved this invoice. '}
          {inv.posted_by && inv.posted_by === user?.id && 'You posted this invoice. '}
        </div>
      )}

      {inv.has_document && <DocumentPreview invoiceId={invoiceId} />}

      <ReclassifyBanner
        invoiceId={invoiceId}
        lineItems={inv.line_items || []}
        onReclassified={() => getInvoice(invoiceId).then(setInv)}
      />

      <div className="detail-grid">
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>Invoice Details</h3>
          {[['Type', inv.invoice_type], ['Invoice #', inv.invoice_number], ['Date', inv.invoice_date], ['Due Date', inv.due_date], ['Currency', inv.currency], ['Project', inv.project_code], ['Cost Center', inv.cost_center], ['Confidence', `${((inv.confidence_score || 0) * 100).toFixed(0)}%`]].map(([l, v], i) => (
            <div key={i} className="detail-row"><span className="detail-label">{l}</span><span className="detail-value">{v || '-'}</span></div>
          ))}
          {/* Vendor link */}
          <div className="detail-row">
            <span className="detail-label">Vendor Master</span>
            <span className="detail-value" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {inv.vendor_id ? (
                <>
                  <span className="badge badge-posted" style={{ fontSize: 11 }}>
                    Linked {inv.vendor_match_confidence < 1.0 ? `(${(inv.vendor_match_confidence * 100).toFixed(0)}% auto)` : '(manual)'}
                  </span>
                  <button className="btn btn-sm" onClick={() => { unlinkInvoiceVendor(invoiceId).then(() => getInvoice(invoiceId).then(setInv)).catch(e => alert(e.message)); }}>Unlink</button>
                </>
              ) : (
                <>
                  <span className="text-muted text-xs">Not linked</span>
                  <VendorLinkDropdown invoiceId={invoiceId} onLinked={() => getInvoice(invoiceId).then(setInv)} />
                </>
              )}
            </span>
          </div>
          {/* Assignee */}
          <div className="detail-row">
            <span className="detail-label">Assigned To</span>
            <span className="detail-value" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AssigneeDropdown
                currentAssignee={inv.assigned_to}
                onAssign={(userId) => assignInvoice(invoiceId, userId).then(() => getInvoice(invoiceId).then(setInv)).catch(e => alert(e.message))}
              />
            </span>
          </div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>Amounts</h3>
          {[['Subtotal', fmtCurrency(inv.subtotal, inv.currency)], ['VAT', fmtCurrency(inv.tax_total, inv.currency)]].map(([l, v], i) => (
            <div key={i} className="detail-row"><span className="detail-label">{l}</span><span className="detail-value">{v}</span></div>
          ))}
          <div className="detail-total">
            <span className="detail-total-label">Total</span>
            <span className="detail-total-value">{fmtCurrency(inv.total_amount, inv.currency)}</span>
          </div>
        </div>
      </div>

      {/* TDS Section */}
      {inv.tds_applicable && (
        <div className="card" style={{ padding: 20, borderColor: 'var(--amber)', borderWidth: 1, borderStyle: 'solid' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Tax Deducted at Source (TDS)</h3>
            <span className="badge" style={{ background: 'var(--amber-muted)', color: 'var(--amber)' }}>TDS @ {inv.tds_rate}%</span>
          </div>
          <div className="detail-grid">
            <div className="detail-row"><span className="detail-label">Gross Amount</span><span className="detail-value">{fmtCurrency(inv.total_amount, inv.currency)}</span></div>
            <div className="detail-row"><span className="detail-label">TDS Amount</span><span className="detail-value" style={{ color: 'var(--red)' }}>-{fmtCurrency(inv.tds_amount || (inv.total_amount * inv.tds_rate / 100), inv.currency)}</span></div>
            <div className="detail-total">
              <span className="detail-total-label">Net to Supplier</span>
              <span className="detail-total-value" style={{ color: 'var(--accent)' }}>{fmtCurrency((inv.total_amount - (inv.tds_amount || inv.total_amount * inv.tds_rate / 100)), inv.currency)}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">MRA Status</span>
              <span className="detail-value">{inv.tds_paid_to_mra ? `Remitted ${inv.tds_paid_date || ''}` : 'Pending remittance'}</span>
            </div>
          </div>
          {!inv.tds_paid_to_mra && inv.status === 'paid' && (
            <button className="btn btn-sm" style={{ marginTop: 12, borderColor: 'var(--amber)', color: 'var(--amber)' }} onClick={() => { markTdsRemitted(inv.invoice_id).then(() => getInvoice(invoiceId).then(setInv)).catch(e => alert(e.message)); }}>
              Mark TDS Remitted to MRA
            </button>
          )}
        </div>
      )}

      {/* TDS Override (only for admin, before payment) */}
      {inv.status !== 'paid' && (
        <TdsOverride invoice={inv} onUpdate={(tdsApplicable, tdsRate) => updateInvoiceTds(invoiceId, tdsApplicable, tdsRate).then(() => getInvoice(invoiceId).then(setInv))} />
      )}

      {(inv.line_items || []).length > 0 && (
        <div className="card">
          <div className="card-header"><h3>Line Items</h3></div>
          <table className="data-table">
            <thead><tr><th>#</th><th>Description</th><th>Qty</th><th>Unit Price</th><th>Amount</th><th>Account</th></tr></thead>
            <tbody>{inv.line_items.map((it, i) => (
              <tr key={i}>
                <td className="text-muted">{it.line_number}</td><td>{it.description}</td>
                <td className="mono text-sm">{it.quantity}</td><td className="mono text-sm">{fmtCurrency(it.unit_price, inv.currency)}</td>
                <td className="mono text-sm">{fmtCurrency(it.amount, inv.currency)}</td><td className="mono text-xs text-accent">{it.account_code || '-'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {(inv.journal_entries || []).length > 0 && (
        <div className="card">
          <div className="card-header"><h3>Journal Entries</h3></div>
          {inv.journal_entries.map((entry, ei) => (
            <div key={ei} className="je-block">
              <div className="je-header">
                <div><span className="je-ref">{entry.entry_id}</span></div>
                <div className="je-meta">
                  <StatusBadge status={entry.status} />
                  {entry.is_balanced && <span className="je-balanced"><Icons.Check /> Balanced</span>}
                </div>
              </div>
              <table className="data-table">
                <thead><tr><th>Account</th><th>Description</th><th className="text-right">Debit</th><th className="text-right">Credit</th></tr></thead>
                <tbody>
                  {(entry.lines || []).map((l, li) => (
                    <tr key={li}>
                      <td><span className="mono text-xs text-accent">{l.account_code}</span> <span className="text-muted text-xs">{l.account_name}</span></td>
                      <td className="text-muted text-xs">{l.description}</td>
                      <td className="text-right debit">{l.debit > 0 ? fmtCurrency(l.debit, inv.currency) : ''}</td>
                      <td className="text-right credit">{l.credit > 0 ? fmtCurrency(l.credit, inv.currency) : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   JOURNAL ENTRIES
   ═══════════════════════════════════════════════════════ */
function JournalEntries() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const { user, selectedCompany } = useAuth();

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await getJournalEntries(filter ? { status: filter } : {}); setEntries(r.entries || []); }
    catch (e) { console.error(e); } finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Journal Entries</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={async () => {
            try { await exportJournalEntriesSage200(filter || 'posted'); }
            catch (e) { alert(e.message); }
          }}>Export to Sage 200</button>
          <button className="btn btn-primary" onClick={async () => {
            try { await exportJournalEntriesExcel(filter || 'posted'); }
            catch (e) { alert(e.message); }
          }}><Icons.Download /> Export to Excel</button>
        </div>
      </div>
      <div className="filter-bar">
        {['', 'draft', 'posted', 'reversed'].map(s => (
          <button key={s} className={`filter-pill ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>{s || 'All'}</button>
        ))}
      </div>

      {loading ? <Loading /> : entries.length === 0 ? <Empty text="No journal entries found" /> : entries.map(entry => (
        <div key={entry.entry_id} className="card animate-fade-in">
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <div>
              <span className="je-ref">{entry.entry_id}</span>
              <span className="je-desc"> — {entry.description}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 8 }}>{entry.entry_date}</span>
            </div>
            <div className="je-meta">
              <StatusBadge status={entry.status} />
              {entry.status === 'draft' && <button className="btn btn-primary btn-sm" onClick={() => postJournalEntry(entry.entry_id).then(load)}>Post</button>}
              {entry.status === 'posted' && (
                <button
                  className="btn btn-danger btn-sm"
                  disabled={selectedCompany?.maker_checker_enabled && entry.posted_by === user?.id}
                  title={selectedCompany?.maker_checker_enabled && entry.posted_by === user?.id ? 'Maker/checker: another user must reverse this entry' : ''}
                  onClick={() => { if (confirm('Create reversing entry?')) reverseJournalEntry(entry.entry_id).then(load); }}
                >Reverse</button>
              )}
            </div>
          </div>
          <table className="data-table">
            <thead><tr><th>Account</th><th>Description</th><th className="text-right">Debit</th><th className="text-right">Credit</th></tr></thead>
            <tbody>
              {(entry.lines || []).map((l, i) => (
                <tr key={i}>
                  <td><span className="mono text-xs text-accent">{l.account_code}</span> <span className="text-muted text-xs">{l.account_name}</span></td>
                  <td className="text-muted text-xs">{l.description}</td>
                  <td className="text-right debit">{l.debit > 0 ? fmtCurrency(l.debit, entry.currency) : ''}</td>
                  <td className="text-right credit">{l.credit > 0 ? fmtCurrency(l.credit, entry.currency) : ''}</td>
                </tr>
              ))}
              <tr className="je-totals-row">
                <td colSpan={2} style={{ textAlign: 'right', fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Totals</td>
                <td className="text-right debit">{fmtCurrency(entry.total_debit, entry.currency)}</td>
                <td className="text-right credit">{fmtCurrency(entry.total_credit, entry.currency)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   CHART OF ACCOUNTS
   ═══════════════════════════════════════════════════════ */

function LearnedRules() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await getClassificationRules(); setRules(r.rules || []); }
    catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id) => {
    if (!confirm('Delete this learned rule?')) return;
    try { await deleteClassificationRule(id); load(); }
    catch (e) { alert(e.message); }
  };

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Learned Classification Rules</h2>
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
        These rules were learned from your reclassifications. When a new invoice arrives from a known vendor,
        the system will automatically assign the correct GL account based on these rules.
      </p>
      {loading ? <Loading /> : rules.length === 0 ? (
        <Empty text="No learned rules yet. Rules are created when you reclassify invoices." />
      ) : (
        <div className="card">
          <table className="data-table">
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Account</th>
                <th>User Context</th>
                <th>Used</th>
                <th>Learned</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map(r => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 500, color: 'var(--text-white)' }}>{r.vendor_name || '-'}</td>
                  <td>
                    <span className="mono text-xs text-accent">{r.account_code}</span>
                    <span className="text-muted text-xs" style={{ marginLeft: 4 }}>{r.account_name}</span>
                  </td>
                  <td className="text-muted text-sm" style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.user_context || '-'}</td>
                  <td className="mono text-sm">{r.times_used}x</td>
                  <td className="text-muted text-xs">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}</td>
                  <td><button className="btn btn-danger btn-sm" onClick={() => handleDelete(r.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ChartOfAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    setLoading(true);
    getChartOfAccounts(filter).then(r => setAccounts(r.accounts || [])).catch(console.error).finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header"><h2>Chart of Accounts</h2></div>
      <div className="filter-bar">
        {['', 'asset', 'liability', 'equity', 'revenue', 'expense'].map(c => (
          <button key={c} className={`filter-pill ${filter === c ? 'active' : ''}`} onClick={() => setFilter(c)}>
            {c || 'All'}
          </button>
        ))}
      </div>

      <div className="card">
        {loading ? <Loading /> : (
          <table className="data-table">
            <thead><tr><th>Code</th><th>Account Name</th><th>Category</th><th>Parent</th></tr></thead>
            <tbody>{accounts.map(a => (
              <tr key={a.code}>
                <td className="mono text-sm text-accent">{a.code}</td>
                <td style={a.parent_code ? { paddingLeft: 36 } : { fontWeight: 500 }}>{a.name}</td>
                <td className={`text-xs cat-${a.category}`} style={{ textTransform: 'capitalize' }}>{a.category}</td>
                <td className="mono text-xs text-muted">{a.parent_code || '-'}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   MAIN APP
   ═══════════════════════════════════════════════════════ */

function AuditLog() {
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await getAuditLog(action ? { action } : {}); setEntries(r.entries || []); setTotal(r.total || 0); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [action]);

  useEffect(() => { load(); }, [load]);

  const actionColors = {
    invoice_approved: 'badge-posted',
    invoice_posted: 'badge-posted',
    invoice_rejected: 'badge-rejected',
    invoice_paid: 'badge-posted',
    invoice_deleted: 'badge-rejected',
    journal_posted: 'badge-posted',
    journal_reversed: 'badge-rejected',
    data_reset: 'badge-rejected',
    tds_override: 'badge-pending_review',
    tds_remitted: 'badge-posted',
  };

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Audit Log <span className="count">({total})</span></h2>
      </div>
      <div className="filter-bar">
        {['', 'invoice_approved', 'invoice_posted', 'invoice_paid', 'invoice_deleted', 'journal_posted', 'journal_reversed', 'data_reset', 'tds_override', 'tds_remitted'].map(a => (
          <button key={a} className={`filter-pill ${action === a ? 'active' : ''}`} onClick={() => setAction(a)}>
            {a ? a.replace(/_/g, ' ') : 'All'}
          </button>
        ))}
      </div>
      <div className="card">
        {loading ? <Loading /> : (
          <table className="data-table">
            <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Description</th></tr></thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i}>
                  <td className="text-xs text-muted">{e.timestamp ? new Date(e.timestamp).toLocaleString() : '-'}</td>
                  <td className="text-sm">{e.user_email || '-'}</td>
                  <td><span className={`badge ${actionColors[e.action] || 'badge-draft'}`}>{e.action.replace(/_/g, ' ')}</span></td>
                  <td className="text-xs">{e.description || '-'}</td>
                </tr>
              ))}
              {entries.length === 0 && <tr><td colSpan={4}><Empty text="No audit entries found" /></td></tr>}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function TdsRegister() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await getTdsRegister(startDate || undefined, endDate || undefined); setData(r); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [startDate, endDate]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Loading />;
  if (!data || data.entries.length === 0) return (
    <div className="animate-fade-in space-y">
      <div className="page-header"><h2>TDS Register</h2></div>
      <Empty text="No TDS deductions found for this period" />
    </div>
  );

  const s = data.summary;

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header"><h2>TDS Register — {data.company}</h2></div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <input type="date" className="input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        <span className="text-muted">to</span>
        <input type="date" className="input" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
      </div>
      <div className="stats-grid">
        <div className="stat-card"><div className="stat-card-header"><span className="stat-card-label">Deductions</span></div><div className="stat-card-value">{s.count}</div></div>
        <div className="stat-card"><div className="stat-card-header"><span className="stat-card-label">Gross Paid</span></div><div className="stat-card-value">{fmtCurrency(s.total_gross)}</div></div>
        <div className="stat-card" style={{ borderColor: 'var(--amber)' }}><div className="stat-card-header"><span className="stat-card-label">Total TDS</span></div><div className="stat-card-value amber">{fmtCurrency(s.total_tds)}</div></div>
        <div className="stat-card"><div className="stat-card-header"><span className="stat-card-label">Net to Suppliers</span></div><div className="stat-card-value accent">{fmtCurrency(s.total_net)}</div></div>
      </div>
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Date</th><th>Vendor</th><th>Invoice #</th><th>Gross</th><th>Rate</th><th>TDS Amount</th><th>Net Paid</th><th>MRA Status</th></tr></thead>
          <tbody>
            {data.entries.map((e, i) => (
              <tr key={i}>
                <td className="text-xs text-muted">{e.invoice_date}</td>
                <td>{e.vendor_name}</td>
                <td className="mono text-xs text-accent">{e.invoice_number}</td>
                <td className="mono text-sm">{fmtCurrency(e.total_amount)}</td>
                <td className="mono text-sm">{e.tds_rate}%</td>
                <td className="mono text-sm" style={{ color: 'var(--red)' }}>{fmtCurrency(e.tds_amount)}</td>
                <td className="mono text-sm" style={{ color: 'var(--accent)' }}>{fmtCurrency(e.net_amount)}</td>
                <td>{e.tds_paid_to_mra ? <span className="badge badge-posted">Remitted</span> : <span className="badge badge-pending_review">Pending</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExchangeRates() {
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState({});
  const { isAdmin } = useAuth();

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await getExchangeRates(); setRates(r.rates || []); }
    catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (currency) => {
    try { await updateExchangeRate(currency, editing[currency]); load(); setEditing({ ...editing, [currency]: undefined }); }
    catch (e) { alert(e.message); }
  };

  const handleRefresh = async () => {
    try { await refreshExchangeRates(); load(); }
    catch (e) { alert(e.message); }
  };

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Exchange Rates</h2>
        {isAdmin() && <button className="btn btn-primary" onClick={handleRefresh}>Refresh from API</button>}
      </div>
      <p className="text-muted" style={{ fontSize: 13, marginBottom: 16 }}>
        Global rates relative to MUR (base currency). Used for invoice conversion and FX gain/loss calculation.
      </p>
      {loading ? <Loading /> : (
        <div className="card">
          <table className="data-table">
            <thead><tr><th>Currency</th><th>Rate (to MUR)</th><th>Date</th><th>Source</th><th>Actions</th></tr></thead>
            <tbody>
              {rates.map(r => (
                <tr key={r.currency}>
                  <td className="mono text-sm" style={{ fontWeight: 600, color: 'var(--accent)' }}>{r.currency}</td>
                  <td>
                    {editing[r.currency] !== undefined ? (
                      <input type="number" step="0.0001" className="input" style={{ width: 100 }}
                        value={editing[r.currency]} onChange={(e) => setEditing({ ...editing, [r.currency]: parseFloat(e.target.value) || 0 })} />
                    ) : r.rate_to_mur}
                  </td>
                  <td className="text-xs text-muted">{r.date}</td>
                  <td className="text-xs">{r.source}</td>
                  <td>
                    {isAdmin() && (
                      editing[r.currency] !== undefined ? (
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button className="btn btn-sm btn-primary" onClick={() => handleSave(r.currency)}>Save</button>
                          <button className="btn btn-sm" onClick={() => setEditing({ ...editing, [r.currency]: undefined })}>Cancel</button>
                        </div>
                      ) : (
                        <button className="btn btn-sm" onClick={() => setEditing({ ...editing, [r.currency]: r.rate_to_mur })}>Edit</button>
                      )
                    )}
                  </td>
                </tr>
              ))}
              {rates.length === 0 && <tr><td colSpan={5}><Empty text="No exchange rates. Click Refresh to fetch from API." /></td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RecurringInvoices() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recurringEnabled, setRecurringEnabled] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', vendor_name: '', invoice_type: 'supplier', frequency: 'monthly', day_of_month: 1, total_amount: 0, tds_applicable: false, tds_rate: 0, auto_post: false, currency: 'MUR', line_items: '[]' });
  const { user, selectedCompany, refreshUser } = useAuth();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getRecurringTemplates();
      setTemplates(r.templates || []);
      setRecurringEnabled(r.recurring_enabled || false);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggleCompany = async () => {
    try { await toggleRecurringCompany(selectedCompany.id, !recurringEnabled); await refreshUser(); load(); }
    catch (e) { alert(e.message); }
  };

  const handleSubmit = async () => {
    try {
      const data = { ...form, line_items: form.line_items ? JSON.parse(form.line_items) : [], tds_applicable: form.tds_applicable };
      if (editing) { await updateRecurringTemplate(editing, data); }
      else { await createRecurringTemplate(data); }
      setShowForm(false); setEditing(null);
      setForm({ name: '', vendor_name: '', invoice_type: 'supplier', frequency: 'monthly', day_of_month: 1, total_amount: 0, tds_applicable: false, tds_rate: 0, auto_post: false, currency: 'MUR', line_items: '[]' });
      load();
    } catch (e) { alert(e.message); }
  };

  const handleEdit = (t) => {
    setEditing(t.id);
    setForm({ name: t.name, vendor_name: t.vendor_name, invoice_type: t.invoice_type, frequency: t.frequency, day_of_month: t.day_of_month, total_amount: t.total_amount, tds_applicable: t.tds_applicable, tds_rate: t.tds_rate, auto_post: t.auto_post, currency: 'MUR', line_items: '[]' });
    setShowForm(true);
  };

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Recurring Invoices</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)' }}>
            <input type="checkbox" checked={recurringEnabled} onChange={handleToggleCompany} />
            Enabled
          </label>
          {recurringEnabled && <button className="btn btn-primary" onClick={() => { setEditing(null); setShowForm(true); }}>+ Add Template</button>}
        </div>
      </div>

      {!recurringEnabled ? (
        <Empty text="Recurring invoices are disabled. Toggle 'Enabled' above to activate (admin only)." />
      ) : loading ? <Loading /> : (
        <div className="card">
          <table className="data-table">
            <thead><tr><th>Name</th><th>Vendor</th><th>Frequency</th><th>Amount</th><th>Next Gen</th><th>Last Gen</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {templates.map(t => (
                <tr key={t.id}>
                  <td style={{ fontWeight: 500 }}>{t.name}</td>
                  <td>{t.vendor_name}</td>
                  <td className="text-xs">{t.frequency} (day {t.day_of_month})</td>
                  <td className="mono text-sm">{t.total_amount > 0 ? fmtCurrency(t.total_amount, t.currency) : 'Variable'}</td>
                  <td className="text-xs text-muted">{t.next_generation || '-'}</td>
                  <td className="text-xs text-muted">{t.last_generated || 'Never'}</td>
                  <td>{t.is_active ? <span className="badge badge-posted">Active</span> : <span className="badge badge-draft">Paused</span>}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-sm btn-primary" onClick={() => generateRecurringNow(t.id).then(() => load()).catch(e => alert(e.message))}>Generate Now</button>
                      <button className="btn btn-sm" onClick={() => handleEdit(t)}>Edit</button>
                      <button className="btn btn-sm" onClick={() => toggleRecurringTemplate(t.id).then(() => load())}>{t.is_active ? 'Pause' : 'Resume'}</button>
                      <button className="btn btn-danger btn-sm" onClick={() => { if (confirm('Delete this template?')) deleteRecurringTemplate(t.id).then(() => load()); }}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {templates.length === 0 && <tr><td colSpan={8}><Empty text="No recurring templates yet." /></td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {showForm && recurringEnabled && (
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ marginBottom: 16 }}>{editing ? 'Edit Template' : 'New Recurring Template'}</h3>
          <div className="form-grid">
            <div><label className="input-label">Name</label><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Monthly Electricity" /></div>
            <div><label className="input-label">Vendor Name</label><input className="input" value={form.vendor_name} onChange={(e) => setForm({ ...form, vendor_name: e.target.value })} /></div>
            <div>
              <label className="input-label">Frequency</label>
              <select className="input" value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })}>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annually">Annually</option>
              </select>
            </div>
            <div><label className="input-label">Day of Month</label><input type="number" min={1} max={28} className="input" value={form.day_of_month} onChange={(e) => setForm({ ...form, day_of_month: parseInt(e.target.value) || 1 })} /></div>
            <div><label className="input-label">Total Amount (0 = variable)</label><input type="number" step="0.01" className="input" value={form.total_amount} onChange={(e) => setForm({ ...form, total_amount: parseFloat(e.target.value) || 0 })} /></div>
            <div><label className="input-label">TDS Rate %</label><input type="number" step="0.1" className="input" value={form.tds_rate} onChange={(e) => setForm({ ...form, tds_rate: parseFloat(e.target.value) || 0 })} /></div>
            <div><label className="input-label">Currency</label><select className="input" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}><option value="MUR">MUR</option><option value="USD">USD</option><option value="EUR">EUR</option><option value="GBP">GBP</option><option value="ZAR">ZAR</option></select></div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}><input type="checkbox" checked={form.tds_applicable} onChange={(e) => setForm({ ...form, tds_applicable: e.target.checked })} /> TDS Applicable</label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}><input type="checkbox" checked={form.auto_post} onChange={(e) => setForm({ ...form, auto_post: e.target.checked })} /> Auto-Post</label>
            </div>
          </div>
          <div className="btn-group" style={{ marginTop: 16 }}>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={!form.name || !form.vendor_name}>{editing ? 'Update' : 'Create'}</button>
            <button className="btn" onClick={() => { setShowForm(false); setEditing(null); }}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

function VendorMaster() {
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', aliases: '', brn: '', vat: '', default_tds_rate: 0, payment_terms: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await getVendors(search || undefined); setVendors(r.vendors || []); }
    catch (e) { console.error(e); } finally { setLoading(false); }
  }, [search]);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async () => {
    try {
      const data = { ...form, aliases: form.aliases ? form.aliases.split(',').map(s => s.trim()).filter(Boolean) : [] };
      if (editing) {
        await updateVendor(editing, data);
      } else {
        await createVendor(data);
      }
      setShowForm(false); setEditing(null);
      setForm({ name: '', aliases: '', brn: '', vat: '', default_tds_rate: 0, payment_terms: '' });
      load();
    } catch (e) { alert(e.message); }
  };

  const handleEdit = (v) => {
    setEditing(v.id);
    setForm({ name: v.name, aliases: (v.aliases || []).join(', '), brn: v.brn || '', vat: v.vat || '', default_tds_rate: v.default_tds_rate || 0, payment_terms: v.payment_terms || '' });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this vendor? Invoices linked to it will be unlinked.')) return;
    try { await deleteVendor(id); load(); } catch (e) { alert(e.message); }
  };

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Vendors <span className="count">({vendors.length})</span></h2>
        <button className="btn btn-primary" onClick={() => { setEditing(null); setForm({ name: '', aliases: '', brn: '', vat: '', default_tds_rate: 0, payment_terms: '' }); setShowForm(true); }}>+ Add Vendor</button>
      </div>

      <input className="input" style={{ width: 260 }} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search vendors..." />

      {showForm && (
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ marginBottom: 16 }}>{editing ? 'Edit Vendor' : 'New Vendor'}</h3>
          <div className="form-grid">
            <div><label className="input-label">Name</label><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Vendor name" /></div>
            <div><label className="input-label">Aliases (comma-separated)</label><input className="input" value={form.aliases} onChange={(e) => setForm({ ...form, aliases: e.target.value })} placeholder="PwC, PWC, PricewaterhouseCoopers" /></div>
            <div><label className="input-label">BRN</label><input className="input" value={form.brn} onChange={(e) => setForm({ ...form, brn: e.target.value })} /></div>
            <div><label className="input-label">VAT</label><input className="input" value={form.vat} onChange={(e) => setForm({ ...form, vat: e.target.value })} /></div>
            <div><label className="input-label">Default TDS Rate (%)</label><input type="number" step="0.1" className="input" value={form.default_tds_rate} onChange={(e) => setForm({ ...form, default_tds_rate: parseFloat(e.target.value) || 0 })} /></div>
            <div><label className="input-label">Payment Terms</label><input className="input" value={form.payment_terms} onChange={(e) => setForm({ ...form, payment_terms: e.target.value })} placeholder="Net 30" /></div>
          </div>
          <div className="btn-group" style={{ marginTop: 16 }}>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={!form.name}>{editing ? 'Update' : 'Create'}</button>
            <button className="btn" onClick={() => { setShowForm(false); setEditing(null); }}>Cancel</button>
          </div>
        </div>
      )}

      {loading ? <Loading /> : (
        <div className="card">
          <table className="data-table">
            <thead><tr><th>Name</th><th>BRN</th><th>VAT</th><th>TDS %</th><th>Terms</th><th>Actions</th></tr></thead>
            <tbody>
              {vendors.map(v => (
                <tr key={v.id}>
                  <td style={{ fontWeight: 500 }}>
                    {v.name}
                    {(v.aliases || []).length > 0 && <span className="text-muted text-xs" style={{ marginLeft: 6 }}>aka {v.aliases.join(', ')}</span>}
                  </td>
                  <td className="mono text-xs">{v.brn || '-'}</td>
                  <td className="mono text-xs">{v.vat || '-'}</td>
                  <td className="mono text-sm">{v.default_tds_rate > 0 ? `${v.default_tds_rate}%` : '-'}</td>
                  <td className="text-xs">{v.payment_terms || '-'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-sm" onClick={() => handleEdit(v)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(v.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {vendors.length === 0 && <tr><td colSpan={6}><Empty text="No vendors yet. Add your first vendor to enable auto-matching." /></td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AppLayout() {
  const { user, logout, isAdmin, selectedCompany, selectCompany } = useAuth();
  const navigate = useNavigate();
  const [view, setView] = useState('dashboard');
  const [selectedId, setSelectedId] = useState(null);
  const [health, setHealth] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('fp-theme') || 'dark');
  const [resetting, setResetting] = useState(false);
  const [companyKey, setCompanyKey] = useState(0);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('fp-theme', theme);
  }, [theme]);

  useEffect(() => {
    checkHealth().then(() => setHealth(true)).catch(() => setHealth(false));
    const t = setInterval(() => { checkHealth().then(() => setHealth(true)).catch(() => setHealth(false)); }, 30000);
    return () => clearInterval(t);
  }, []);

  // Reload all data when company changes
  const handleSelectCompany = (company) => {
    selectCompany(company);
    setView('dashboard');
    setSelectedId(null);
    setCompanyKey(k => k + 1);
  };

  const nav = (v, id = null) => { setView(v); setSelectedId(id); window.scrollTo(0, 0); };

  const handleReset = async () => {
    if (!window.confirm(`This will permanently delete ALL invoices and journal entries for ${selectedCompany?.name || 'the active company'}.\n\nChart of accounts and learned classification rules are kept.\n\nAre you sure?`)) return;
    setResetting(true);
    try {
      await resetAllData();
      setCompanyKey(k => k + 1);
      setView('dashboard');
    } catch (e) {
      alert(`Reset failed: ${e.message}`);
    } finally {
      setResetting(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!selectedCompany) {
    return (
      <div className="auth-loading">
        <div style={{ textAlign: 'center' }}>
          <p style={{ marginBottom: 16 }}>No company assigned. Please contact an administrator.</p>
          <button className="btn btn-primary" onClick={handleLogout}>Sign Out</button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout" key={companyKey}>
      <Sidebar
        active={view}
        onNavigate={nav}
        health={health}
        theme={theme}
        onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        onReset={handleReset}
        resetting={resetting}
        user={user}
        onLogout={handleLogout}
        isAdmin={isAdmin()}
        companies={user?.companies || []}
        selectedCompany={selectedCompany}
        onSelectCompany={handleSelectCompany}
      />
      <main className="main-content">
        {view === 'dashboard' && <Dashboard onNavigate={nav} />}
        {view === 'upload' && <InvoiceUpload onNavigate={nav} />}
        {view === 'invoices' && <InvoiceList onNavigate={nav} />}
        {view === 'detail' && <InvoiceDetail invoiceId={selectedId} onNavigate={nav} />}
        {view === 'entries' && <JournalEntries />}
        {view === 'accounts' && <ChartOfAccounts />}
        {view === 'vendors' && <VendorMaster />}
        {view === 'recurring' && <RecurringInvoices />}
        {view === 'fxrates' && <ExchangeRates />}
        {view === 'rules' && <LearnedRules />}
        {view === 'tds' && <TdsRegister />}
        {view === 'audit' && isAdmin() && <AuditLog />}
        {view === 'admin' && isAdmin() && <AdminPanel />}
      </main>
    </div>
  );
}

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="auth-loading">Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
};

const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="auth-loading">Loading...</div>;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return children;
};

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/*" element={<ProtectedRoute><AppLayout /></ProtectedRoute>} />
    </Routes>
  );
}
