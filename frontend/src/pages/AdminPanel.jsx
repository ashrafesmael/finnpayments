import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  getCompanies, createCompany, deleteCompany,
  getCompanyUsers, assignUserToCompany, removeUserFromCompany,
  toggleMakerChecker, getCompanySmtp, updateCompanySmtp,
} from '../services/api';
import './AdminPanel.css';

const AdminPanel = () => {
  const [users, setUsers] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const { token, user: currentUser, refreshUser } = useAuth();

  const API_URL = import.meta.env.VITE_API_URL || '';

  // Company form
  const [companyForm, setCompanyForm] = useState({ code: '', name: '', currency: 'MUR' });
  const [companyUsers, setCompanyUsers] = useState({});
  const [expandedCompany, setExpandedCompany] = useState(null);
  const [assignEmail, setAssignEmail] = useState({});

  useEffect(() => {
    fetchUsers();
    fetchCompanies();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await fetch(API_URL + '/auth/admin/users', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      } else {
        setError('Failed to fetch users');
      }
    } catch (err) {
      setError('Error fetching users: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchCompanies = async () => {
    try {
      const data = await getCompanies();
      setCompanies(data);
    } catch (err) {
      setError('Error fetching companies: ' + err.message);
    }
  };

  const fetchCompanyUsers = async (companyId) => {
    try {
      const data = await getCompanyUsers(companyId);
      setCompanyUsers(prev => ({ ...prev, [companyId]: data }));
    } catch (err) {
      setError('Error fetching company users: ' + err.message);
    }
  };

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    setError('');
    if (!companyForm.code || !companyForm.name) {
      setError('Company code and name are required');
      return;
    }
    setActionLoading('create-company');
    try {
      await createCompany(companyForm.code, companyForm.name, companyForm.currency);
      setCompanyForm({ code: '', name: '', currency: 'MUR' });
      await fetchCompanies();
      await refreshUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteCompany = async (companyId) => {
    if (!window.confirm('Delete this company? This will NOT delete the invoices/entries (they will be orphaned).')) return;
    setActionLoading('delete-' + companyId);
    try {
      await deleteCompany(companyId);
      await fetchCompanies();
      await refreshUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleMakerChecker = async (companyId, enabled) => {
    setActionLoading('mc-' + companyId);
    try {
      await toggleMakerChecker(companyId, enabled);
      await fetchCompanies();
      await refreshUser();
    } catch (err) {
      setError(err.message);
      await fetchCompanies();
    } finally {
      setActionLoading(null);
    }
  };

  // ── Per-company SMTP settings ──
  const [smtpForm, setSmtpForm] = useState({});
  const [smtpLoaded, setSmtpLoaded] = useState({});

  const loadSmtp = async (companyId) => {
    try {
      const data = await getCompanySmtp(companyId);
      setSmtpForm(prev => ({ ...prev, [companyId]: {
        smtp_host: data.smtp_host || '',
        smtp_port: data.smtp_port || 587,
        smtp_user: data.smtp_user || '',
        smtp_password: '',
        from_email: data.from_email || '',
        from_name: data.from_name || '',
        _configured: data.smtp_configured,
        _hasPassword: !!data.smtp_password,
      }}));
      setSmtpLoaded(prev => ({ ...prev, [companyId]: true }));
    } catch (err) {
      setError('Failed to load SMTP settings: ' + err.message);
    }
  };

  const handleSaveSmtp = async (companyId) => {
    setActionLoading('smtp-' + companyId);
    try {
      const form = smtpForm[companyId];
      const payload = {
        smtp_host: form.smtp_host || null,
        smtp_port: parseInt(form.smtp_port) || null,
        smtp_user: form.smtp_user || null,
        smtp_password: form.smtp_password || null,
        from_email: form.from_email || null,
        from_name: form.from_name || null,
      };
      await updateCompanySmtp(companyId, payload);
      await loadSmtp(companyId);
      setError('');
    } catch (err) {
      setError('Failed to save SMTP settings: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleClearSmtp = async (companyId) => {
    setActionLoading('smtp-clear-' + companyId);
    try {
      await updateCompanySmtp(companyId, {
        smtp_host: null, smtp_port: null, smtp_user: null,
        smtp_password: null, from_email: null, from_name: null,
      });
      await loadSmtp(companyId);
      setError('');
    } catch (err) {
      setError('Failed to clear SMTP settings: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleApprove = async (userId) => {
    setActionLoading(userId);
    try {
      const response = await fetch(API_URL + '/auth/admin/approve/' + userId, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (response.ok) {
        fetchUsers();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to approve user');
      }
    } catch (err) {
      setError('Error: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (userId) => {
    setActionLoading(userId);
    try {
      const response = await fetch(API_URL + '/auth/admin/reject/' + userId, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (response.ok) {
        fetchUsers();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to reject user');
      }
    } catch (err) {
      setError('Error: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    setActionLoading(userId);
    try {
      const response = await fetch(API_URL + '/auth/admin/users/' + userId, {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (response.ok) {
        fetchUsers();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to delete user');
      }
    } catch (err) {
      setError('Error: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleRole = async (userId, currentRole) => {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    setActionLoading(userId);
    try {
      const response = await fetch(API_URL + '/auth/admin/users/' + userId + '/role?role=' + newRole, {
        method: 'PUT',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (response.ok) {
        fetchUsers();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to update role');
      }
    } catch (err) {
      setError('Error: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleAssignUser = async (companyId) => {
    const email = assignEmail[companyId];
    if (!email) return;
    const user = users.find(u => u.email.toLowerCase() === email.toLowerCase());
    if (!user) {
      setError('User not found: ' + email);
      return;
    }
    setActionLoading('assign-' + companyId);
    try {
      await assignUserToCompany(companyId, user.id);
      setAssignEmail(prev => ({ ...prev, [companyId]: '' }));
      await fetchCompanyUsers(companyId);
      await refreshUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRemoveUserFromCompany = async (companyId, userId) => {
    setActionLoading('remove-' + companyId + '-' + userId);
    try {
      await removeUserFromCompany(companyId, userId);
      await fetchCompanyUsers(companyId);
      await refreshUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const toggleCompanyExpand = (companyId) => {
    if (expandedCompany === companyId) {
      setExpandedCompany(null);
    } else {
      setExpandedCompany(companyId);
      if (!companyUsers[companyId]) {
        fetchCompanyUsers(companyId);
      }
      if (!smtpLoaded[companyId]) {
        loadSmtp(companyId);
      }
    }
  };

  const getStatusBadge = (status) => {
    const classes = {
      pending: 'status-badge pending',
      approved: 'status-badge approved',
      rejected: 'status-badge rejected'
    };
    return <span className={classes[status] || 'status-badge'}>{status}</span>;
  };

  const getRoleBadge = (role) => {
    return <span className={'role-badge ' + role}>{role}</span>;
  };

  const pendingUsers = users.filter(u => u.status === 'pending');
  const activeUsers = users.filter(u => u.status === 'approved');
  const rejectedUsers = users.filter(u => u.status === 'rejected');

  if (loading) {
    return <div className="admin-loading">Loading...</div>;
  }

  return (
    <div className="admin-panel">
      <h1>Administration</h1>

      {error && <div className="admin-error" onClick={() => setError('')}>{error}</div>}

      {/* ─── Companies Section ─── */}
      <section className="user-section">
        <h2>Companies ({companies.length})</h2>

        <form onSubmit={handleCreateCompany} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input
            className="input"
            style={{ width: 100 }}
            placeholder="Code (e.g. MCG)"
            value={companyForm.code}
            onChange={(e) => setCompanyForm({ ...companyForm, code: e.target.value.toUpperCase() })}
            maxLength={10}
          />
          <input
            className="input"
            style={{ flex: 1 }}
            placeholder="Company Name"
            value={companyForm.name}
            onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
          />
          <select
            className="input"
            style={{ width: 100 }}
            value={companyForm.currency}
            onChange={(e) => setCompanyForm({ ...companyForm, currency: e.target.value })}
          >
            <option value="MUR">MUR</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="GBP">GBP</option>
            <option value="ZAR">ZAR</option>
          </select>
          <button type="submit" className="btn btn-primary" disabled={actionLoading === 'create-company'}>
            {actionLoading === 'create-company' ? 'Creating...' : 'Add Company'}
          </button>
        </form>

        <table className="users-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Currency</th>
              <th>Maker/Checker</th>
              <th>Users</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {companies.map(c => (
              <React.Fragment key={c.id}>
                <tr>
                  <td className="mono text-sm" style={{ fontWeight: 600, color: 'var(--accent)' }}>{c.code}</td>
                  <td style={{ fontWeight: 500 }}>{c.name}</td>
                  <td className="text-muted text-sm">{c.currency}</td>
                  <td>
                    <label className="mc-toggle" title="Enable maker/checker (requires 2+ users)">
                      <input
                        type="checkbox"
                        checked={c.maker_checker_enabled || false}
                        onChange={() => handleToggleMakerChecker(c.id, !c.maker_checker_enabled)}
                        disabled={actionLoading === 'mc-' + c.id}
                      />
                      <span className="mc-slider"></span>
                    </label>
                  </td>
                  <td className="text-sm">{c.user_count || 0}</td>
                  <td className="action-buttons">
                    <button className="btn-role" onClick={() => toggleCompanyExpand(c.id)} title="Manage users">
                      {expandedCompany === c.id ? '▲' : '▼'}
                    </button>
                    <button
                      className="btn-delete"
                      onClick={() => handleDeleteCompany(c.id)}
                      disabled={actionLoading === 'delete-' + c.id}
                      title="Delete company"
                    >×</button>
                  </td>
                </tr>
                {expandedCompany === c.id && (
                  <tr>
                    <td colSpan={5} style={{ background: 'var(--bg-surface-2)', padding: 16 }}>
                      <div style={{ marginBottom: 12, fontWeight: 500 }}>Users assigned to {c.name}</div>
                      <table className="users-table" style={{ marginBottom: 12 }}>
                        <thead>
                          <tr><th>Name</th><th>Email</th><th>Role</th><th></th></tr>
                        </thead>
                        <tbody>
                          {(companyUsers[c.id] || []).map(u => (
                            <tr key={u.id}>
                              <td>{u.full_name}</td>
                              <td>{u.email}</td>
                              <td>{getRoleBadge(u.role)}</td>
                              <td>
                                {u.id !== currentUser?.id && (
                                  <button
                                    className="btn-delete"
                                    onClick={() => handleRemoveUserFromCompany(c.id, u.id)}
                                    disabled={actionLoading === 'remove-' + c.id + '-' + u.id}
                                  >×</button>
                                )}
                              </td>
                            </tr>
                          ))}
                          {(companyUsers[c.id] || []).length === 0 && (
                            <tr><td colSpan={4} className="text-muted">No users assigned</td></tr>
                          )}
                        </tbody>
                      </table>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <input
                          className="input"
                          style={{ flex: 1 }}
                          placeholder="Enter user email to assign..."
                          value={assignEmail[c.id] || ''}
                          onChange={(e) => setAssignEmail(prev => ({ ...prev, [c.id]: e.target.value }))}
                          onKeyDown={(e) => { if (e.key === 'Enter') handleAssignUser(c.id); }}
                        />
                        <button
                          className="btn btn-primary"
                          onClick={() => handleAssignUser(c.id)}
                          disabled={actionLoading === 'assign-' + c.id}
                        >
                          {actionLoading === 'assign-' + c.id ? 'Assigning...' : 'Assign User'}
                        </button>
                      </div>

                      {/* ── SMTP / Notification Sender Settings ── */}
                      <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                        <div style={{ marginBottom: 8, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
                          Notification Sender (SMTP)
                          {smtpForm[c.id]?._configured && (
                            <span className="badge badge-posted" style={{ fontSize: 10 }}>Configured</span>
                          )}
                          {!smtpForm[c.id]?._configured && (
                            <span className="text-muted text-xs">— using system default</span>
                          )}
                        </div>
                        {smtpForm[c.id] ? (
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                            <input
                              className="input"
                              placeholder="SMTP Host (e.g. smtp.gmail.com)"
                              value={smtpForm[c.id].smtp_host}
                              onChange={(e) => setSmtpForm(prev => ({ ...prev, [c.id]: { ...prev[c.id], smtp_host: e.target.value } }))}
                            />
                            <input
                              className="input"
                              type="number"
                              placeholder="Port (587)"
                              value={smtpForm[c.id].smtp_port}
                              onChange={(e) => setSmtpForm(prev => ({ ...prev, [c.id]: { ...prev[c.id], smtp_port: e.target.value } }))}
                            />
                            <input
                              className="input"
                              placeholder="SMTP Username"
                              value={smtpForm[c.id].smtp_user}
                              onChange={(e) => setSmtpForm(prev => ({ ...prev, [c.id]: { ...prev[c.id], smtp_user: e.target.value } }))}
                            />
                            <input
                              className="input"
                              type="password"
                              placeholder={smtpForm[c.id]._hasPassword ? '••••• (enter new to change)' : 'SMTP Password'}
                              value={smtpForm[c.id].smtp_password}
                              onChange={(e) => setSmtpForm(prev => ({ ...prev, [c.id]: { ...prev[c.id], smtp_password: e.target.value } }))}
                            />
                            <input
                              className="input"
                              placeholder="From Email (e.g. noreply@company.com)"
                              value={smtpForm[c.id].from_email}
                              onChange={(e) => setSmtpForm(prev => ({ ...prev, [c.id]: { ...prev[c.id], from_email: e.target.value } }))}
                            />
                            <input
                              className="input"
                              placeholder="From Name (e.g. Company Name)"
                              value={smtpForm[c.id].from_name}
                              onChange={(e) => setSmtpForm(prev => ({ ...prev, [c.id]: { ...prev[c.id], from_name: e.target.value } }))}
                            />
                            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 8, marginTop: 4 }}>
                              <button
                                className="btn btn-primary"
                                onClick={() => handleSaveSmtp(c.id)}
                                disabled={actionLoading === 'smtp-' + c.id}
                              >
                                {actionLoading === 'smtp-' + c.id ? 'Saving...' : 'Save SMTP'}
                              </button>
                              {smtpForm[c.id]?._configured && (
                                <button
                                  className="btn btn-secondary"
                                  onClick={() => handleClearSmtp(c.id)}
                                  disabled={actionLoading === 'smtp-clear-' + c.id}
                                >
                                  {actionLoading === 'smtp-clear-' + c.id ? 'Clearing...' : 'Clear (use default)'}
                                </button>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="text-muted text-sm">Loading SMTP settings...</div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {companies.length === 0 && (
              <tr><td colSpan={5} className="text-muted">No companies yet</td></tr>
            )}
          </tbody>
        </table>
      </section>

      {/* ─── Pending Users ─── */}
      {pendingUsers.length > 0 && (
        <section className="user-section pending-section">
          <h2>Pending Approval ({pendingUsers.length})</h2>
          <div className="user-cards">
            {pendingUsers.map(user => (
              <div key={user.id} className="user-card pending">
                <div className="user-info">
                  <h3>{user.full_name}</h3>
                  <p>{user.email}</p>
                  <p className="user-date">Registered: {new Date(user.created_at).toLocaleDateString()}</p>
                </div>
                <div className="user-actions">
                  <button className="btn-approve" onClick={() => handleApprove(user.id)} disabled={actionLoading === user.id}>
                    {actionLoading === user.id ? '...' : 'Approve'}
                  </button>
                  <button className="btn-reject" onClick={() => handleReject(user.id)} disabled={actionLoading === user.id}>
                    {actionLoading === user.id ? '...' : 'Reject'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ─── Active Users ─── */}
      <section className="user-section">
        <h2>Active Users ({activeUsers.length})</h2>
        <table className="users-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Companies</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {activeUsers.map(user => (
              <tr key={user.id}>
                <td>{user.full_name}</td>
                <td>{user.email}</td>
                <td>{getRoleBadge(user.role)}</td>
                <td>{getStatusBadge(user.status)}</td>
                <td className="text-sm text-muted">
                  {(user.companies || []).map(c => c.code).join(', ') || '-'}
                </td>
                <td className="action-buttons">
                  {user.id !== currentUser?.id && (
                    <>
                      <button
                        className="btn-role"
                        onClick={() => handleToggleRole(user.id, user.role)}
                        disabled={actionLoading === user.id}
                        title={user.role === 'admin' ? 'Demote to User' : 'Promote to Admin'}
                      >
                        {user.role === 'admin' ? '↓' : '↑'}
                      </button>
                      <button
                        className="btn-delete"
                        onClick={() => handleDelete(user.id)}
                        disabled={actionLoading === user.id}
                      >×</button>
                    </>
                  )}
                  {user.id === currentUser?.id && <span className="you-badge">You</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {rejectedUsers.length > 0 && (
        <section className="user-section rejected-section">
          <h2>Rejected Users ({rejectedUsers.length})</h2>
          <table className="users-table">
            <thead>
              <tr><th>Name</th><th>Email</th><th>Rejected</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {rejectedUsers.map(user => (
                <tr key={user.id}>
                  <td>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>{user.approved_at ? new Date(user.approved_at).toLocaleDateString() : '-'}</td>
                  <td className="action-buttons">
                    <button className="btn-approve" onClick={() => handleApprove(user.id)} disabled={actionLoading === user.id}>Approve</button>
                    <button className="btn-delete" onClick={() => handleDelete(user.id)} disabled={actionLoading === user.id}>×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
};

export default AdminPanel;
