import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, CalendarDays, Download, Settings as SettingsIcon, LogOut, Bot, Loader2, BellRing } from 'lucide-react';
import { useAI } from '../context/AIContext';

export default function Sidebar({ onLogout }) {
  const { status } = useAI();
  
  return (
    <div className="sidebar">
      <h1>Synthbit Technologies</h1>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={20} />
          Dashboard
        </NavLink>
        <NavLink to="/employees" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Users size={20} />
          Employees
        </NavLink>
        <NavLink to="/attendance" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <CalendarDays size={20} />
          Attendance Logs
        </NavLink>
        <NavLink to="/ai" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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
        <NavLink to="/alerts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <BellRing size={20} />
          AI Alerts
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <SettingsIcon size={20} />
          Settings
        </NavLink>
      </nav>
      <div style={{ marginTop: 'auto', paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <button 
          onClick={async () => {
            try {
              const baseUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname || '127.0.0.1'}:8080`;
              const response = await fetch(`${baseUrl}/database/backup`);
              const blob = await response.blob();
              const url = window.URL.createObjectURL(blob);
              const link = document.createElement('a');
              link.href = url;
              link.setAttribute('download', 'ams_backup.db');
              document.body.appendChild(link);
              link.click();
              link.remove();
            } catch (err) {
              console.error("Failed to backup database", err);
              alert("Failed to backup database.");
            }
          }}
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
    </div>
  );
}
