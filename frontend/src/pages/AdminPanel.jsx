import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './AdminPanel.css';

const AdminPanel = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const { token, user: currentUser } = useAuth();

  const API_URL = import.meta.env.VITE_API_URL || '';

  useEffect(() => {
    fetchUsers();
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
    return <div className="admin-loading">Loading users...</div>;
  }

  return (
    <div className="admin-panel">
      <h1>User Management</h1>
      
      {error && <div className="admin-error">{error}</div>}

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
                  <button
                    className="btn-approve"
                    onClick={() => handleApprove(user.id)}
                    disabled={actionLoading === user.id}
                  >
                    {actionLoading === user.id ? '...' : 'Approve'}
                  </button>
                  <button
                    className="btn-reject"
                    onClick={() => handleReject(user.id)}
                    disabled={actionLoading === user.id}
                  >
                    {actionLoading === user.id ? '...' : 'Reject'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="user-section">
        <h2>Active Users ({activeUsers.length})</h2>
        <table className="users-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Approved</th>
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
                <td>{user.approved_at ? new Date(user.approved_at).toLocaleDateString() : '-'}</td>
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
                      >
                        ×
                      </button>
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
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Rejected</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rejectedUsers.map(user => (
                <tr key={user.id}>
                  <td>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>{user.approved_at ? new Date(user.approved_at).toLocaleDateString() : '-'}</td>
                  <td className="action-buttons">
                    <button
                      className="btn-approve"
                      onClick={() => handleApprove(user.id)}
                      disabled={actionLoading === user.id}
                    >
                      Approve
                    </button>
                    <button
                      className="btn-delete"
                      onClick={() => handleDelete(user.id)}
                      disabled={actionLoading === user.id}
                    >
                      ×
                    </button>
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
