import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, CalendarDays, Download, Settings as SettingsIcon, LogOut, Bot, Loader2, BellRing } from 'lucide-react';
import { useAI } from '../context/AIContext';
import { getClientId } from '../services/api';

export default function Sidebar({ onLogout, isOpen, onClose }) {
  const { status } = useAI();
  const location = useLocation();
  const isSettingsActive = location.pathname === '/settings';
  const [showPasswordPrompt, setShowPasswordPrompt] = useState(false);
  const [backupPassword, setBackupPassword] = useState('');
  const [backupError, setBackupError] = useState('');

  const handleBackup = async () => {
    setBackupError('');
    try {
      const baseUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname || '127.0.0.1'}:8080`;
      const response = await fetch(`${baseUrl}/database/backup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Client-ID': getClientId() },
        body: JSON.stringify({ password: backupPassword })
      });
      
      if (!response.ok) {
        setBackupError('Invalid password or backup failed.');
        return;
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'ams_backup.db');
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      setShowPasswordPrompt(false);
      setBackupPassword('');
    } catch (err) {
      console.error("Failed to backup database", err);
      setBackupError('Failed to backup database.');
    }
  };

  return (
    <div className={`sidebar ${isOpen ? 'open' : ''}`}>
      <h1>Synthbit Technologies</h1>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        <NavLink to="/" onClick={onClose} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={20} />
          Dashboard
        </NavLink>
        <NavLink to="/employees" onClick={onClose} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Users size={20} />
          Employees
        </NavLink>
        <NavLink to="/attendance" onClick={onClose} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <CalendarDays size={20} />
          Attendance Logs
        </NavLink>
        <NavLink to="/ai" onClick={onClose} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Bot size={20} />
            AI Assistant
          </div>
          {status.state === 'downloading' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', background: 'rgba(59, 130, 246, 0.1)', color: 'var(--primary)', padding: '2px 6px', borderRadius: '10px' }}>
              <Loader2 size={10} className="animate-spin" />
              Downloading
            </div>
          )}
          {status.state === 'installing' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', background: 'rgba(59, 130, 246, 0.1)', color: 'var(--primary)', padding: '2px 6px', borderRadius: '10px' }}>
              <Loader2 size={10} className="animate-spin" />
              Installing
            </div>
          )}
        </NavLink>
        <NavLink to="/alerts" onClick={onClose} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <BellRing size={20} />
          AI Alerts
        </NavLink>
        <NavLink to="/settings" onClick={onClose} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <SettingsIcon size={20} />
          Settings
        </NavLink>
      </nav>
      {isSettingsActive && (
        <div style={{ paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '12px', flexShrink: 0 }}>
          <button
            onClick={() => { setShowPasswordPrompt(true); setBackupPassword(''); setBackupError(''); }}
            style={{ width: '100%', padding: '10px 15px', background: '#e0e7ff', color: '#4f46e5', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px', fontWeight: '600', transition: 'background 0.2s' }}
          >
            <Download size={20} />
            Backup Database
          </button>
          <button
            onClick={onLogout}
            style={{ width: '100%', padding: '10px 15px', background: 'transparent', color: 'var(--text-muted)', border: '1px solid var(--surface-border)', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px', fontWeight: '600', transition: 'all 0.2s' }}
            onMouseOver={(e) => { e.currentTarget.style.background = '#fee2e2'; e.currentTarget.style.color = '#b91c1c'; }}
            onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
          >
            <LogOut size={20} />
            Logout
          </button>
        </div>
      )}
      
      {showPasswordPrompt && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: '12px', width: '320px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <h3 style={{ margin: '0 0 4px 0', color: 'var(--text-color)' }}>Enter Password</h3>
              <p style={{ margin: 0, fontSize: '14px', color: 'var(--text-muted)' }}>Admin password required for backup</p>
            </div>
            {backupError && <div style={{ color: 'var(--danger)', fontSize: '13px', padding: '8px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '6px' }}>{backupError}</div>}
            <input 
              type="password" 
              className="form-control" 
              value={backupPassword} 
              onChange={e => setBackupPassword(e.target.value)} 
              placeholder="Admin Password"
              autoFocus
              onKeyDown={(e) => { if (e.key === 'Enter') handleBackup(); }}
            />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button 
                onClick={() => setShowPasswordPrompt(false)} 
                className="btn" 
                style={{ background: 'transparent', color: 'var(--text-color)', border: '1px solid var(--surface-border)', padding: '8px 16px' }}
              >
                Cancel
              </button>
              <button onClick={handleBackup} className="btn btn-primary" style={{ padding: '8px 16px' }}>
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
