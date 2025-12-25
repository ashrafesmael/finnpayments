import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, isAdmin } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">
          <span className="brand-icon">◈</span>
          <span className="brand-text">finnverify</span>
        </Link>
      </div>
      
      <div className="navbar-menu">
        <Link to="/" className={isActive('/') ? 'nav-link active' : 'nav-link'}>
          Dashboard
        </Link>
        <Link to="/screening" className={isActive('/screening') ? 'nav-link active' : 'nav-link'}>
          Manual Screening
        </Link>
        <Link to="/upload" className={isActive('/upload') ? 'nav-link active' : 'nav-link'}>
          Document Upload
        </Link>
        {isAdmin() && (
          <Link to="/admin" className={isActive('/admin') ? 'nav-link active admin-link' : 'nav-link admin-link'}>
            User Management
          </Link>
        )}
      </div>

      <div className="navbar-user">
        <div 
          className="user-menu-trigger"
          onClick={() => setShowUserMenu(!showUserMenu)}
        >
          <div className="user-avatar">
            {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
          </div>
          <div className="user-info">
            <span className="user-name">{user?.full_name || 'User'}</span>
            <span className="user-role">{user?.role || 'user'}</span>
          </div>
          <span className="dropdown-arrow">▼</span>
        </div>
        
        {showUserMenu && (
          <div className="user-dropdown">
            <div className="dropdown-header">
              <strong>{user?.full_name}</strong>
              <span>{user?.email}</span>
            </div>
            <div className="dropdown-divider"></div>
            <button className="dropdown-item logout" onClick={handleLogout}>
              Sign Out
            </button>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
