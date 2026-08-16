import React, { useState, useRef } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import './Login.css';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const calledRef = useRef(false);

  const API_URL = import.meta.env.VITE_API_URL || '';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    if (!/[A-Z]/.test(password)) {
      setError('Password must contain at least one uppercase letter');
      return;
    }
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]/.test(password)) {
      setError('Password must contain at least one special character');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(API_URL + '/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Reset failed');
      }
      setSuccess('Password reset successfully! Redirecting to login...');
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="login-container">
        <div className="login-box">
          <div className="login-header">
            <h1>finnpayments</h1>
            <p>AI Invoice Processing & Accounting</p>
          </div>
          <div className="login-form">
            <h2>Invalid Link</h2>
            <div className="error-message">This password reset link is invalid or missing a token.</div>
            <div className="login-footer">
              <p><Link to="/forgot-password">Request a new reset link</Link></p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>finnpayments</h1>
          <p>AI Invoice Processing & Accounting</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <h2>Set New Password</h2>

          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}

          <div className="form-group">
            <label htmlFor="password">New Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your new password"
              required
            />
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>

        <div className="login-footer">
          <p><Link to="/login">← Back to Sign In</Link></p>
        </div>
      </div>
    </div>
  );
};

export default ResetPassword;
