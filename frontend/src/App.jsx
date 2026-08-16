import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import {
  getDashboardStats, getInvoices, getInvoice, uploadInvoice,
  updateInvoiceStatus, deleteInvoice, getJournalEntries,
  postJournalEntry, reverseJournalEntry, getChartOfAccounts, checkHealth,
  exportJournalEntriesExcel,
  exportJournalEntriesSage200,
  getInvoiceDocumentUrl,
  getInvoiceDocumentPreview,
  reclassifyInvoice,
  getClassificationRules, deleteClassificationRule, resetAllData
} from './services/api.js';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
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
    { id: 'rules', label: 'Learned Rules', icon: Icons.Brain },
    ...(isAdmin ? [{ id: 'admin', label: 'User Management', icon: Icons.Users }] : []),
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">fp</div>
        <div className="sidebar-logo-text">
          <h1>finnpayments</h1>
          <p>AlgoDynamix</p>
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
        <button className="sidebar-footer-btn danger" onClick={onReset} disabled={resetting} title="Delete all invoices and journal entries for the active company">
          <span className={resetting ? 'spinning' : ''} style={{ display: 'flex' }}><Icons.Refresh /></span>
          {resetting ? 'Resetting…' : 'Reset Data'}
        </button>
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

  useEffect(() => { getDashboardStats().then(setStats).catch(console.error).finally(() => setLoading(false)); }, []);

  if (loading) return <Loading />;
  if (!stats) return <Empty text="Failed to load dashboard" />;

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Dashboard</h2>
        <button className="btn btn-primary" onClick={() => onNavigate('upload')}>Upload Invoice</button>
      </div>

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
          <h3>Recent Invoices</h3>
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
              <tr><td colSpan={5}><Empty text="No invoices yet. Upload your first invoice to get started." /></td></tr>
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
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const ref = useRef(null);

  const handleDrop = useCallback((e) => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setError(null);
    try { setResult(await uploadInvoice(file, invoiceType, projectCode, costCenter)); }
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

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await getInvoices({ ...(filter && { status: filter }), ...(search && { search }) }); setInvoices(r.invoices || []); setTotal(r.total || 0); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filter, search]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Invoices <span className="count">({total})</span></h2>
        <button className="btn btn-primary" onClick={() => onNavigate('upload')}>+ Upload</button>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="input" style={{ width: 260 }} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search vendor or invoice #..." />
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

function InvoiceDetail({ invoiceId, onNavigate }) {
  const [inv, setInv] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { getInvoice(invoiceId).then(setInv).catch(console.error).finally(() => setLoading(false)); }, [invoiceId]);

  const changeStatus = async (s) => { try { await updateInvoiceStatus(invoiceId, s); setInv(await getInvoice(invoiceId)); } catch (e) { alert(e.message); } };

  if (loading) return <Loading />;
  if (!inv) return <Empty text="Invoice not found" />;

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
        {inv.status === 'approved' && <button className="btn btn-primary" onClick={() => changeStatus('posted')}>Post to GL</button>}
        {inv.status === 'posted' && <button className="btn btn-green" onClick={() => changeStatus('paid')}>Mark as Paid</button>}
      </div>

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
              {entry.status === 'posted' && <button className="btn btn-danger btn-sm" onClick={() => { if (confirm('Create reversing entry?')) reverseJournalEntry(entry.entry_id).then(load); }}>Reverse</button>}
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
        {view === 'rules' && <LearnedRules />}
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
      <Route path="/*" element={<ProtectedRoute><AppLayout /></ProtectedRoute>} />
    </Routes>
  );
}
