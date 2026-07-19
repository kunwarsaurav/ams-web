import React, { useState } from 'react';
import { User, KeyRound, CheckCircle2 } from 'lucide-react';

export default function Settings() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handlePasswordChange = (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    const actualCurrentPassword = localStorage.getItem('adminPassword') || 'admin123';

    if (currentPassword !== actualCurrentPassword) {
      setError('Current password is incorrect');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters');
      return;
    }

    localStorage.setItem('adminPassword', newPassword);
    setMessage('Password changed successfully!');
    
    // Reset form
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="settings-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Settings</h2>
          <p className="page-subtitle">Manage your account and system preferences</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px' }}>
        
        {/* Profile Card */}
        <div className="card" style={{ height: 'fit-content' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <User size={24} color="var(--primary)" />
            <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px', textTransform: 'none' }}>Administrator Profile</h3>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px', textTransform: 'uppercase' }}>Username</label>
              <div style={{ fontSize: '16px', fontWeight: '600' }}>admin</div>
            </div>
            <div>
              <label style={{ display: 'block', color: 'var(--text-muted)', fontSize: '12px', marginBottom: '4px', textTransform: 'uppercase' }}>Role</label>
              <div style={{ display: 'inline-block', background: 'var(--primary)', color: 'white', padding: '4px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: '600' }}>Super Admin</div>
            </div>
          </div>
        </div>

        {/* Change Password Card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <KeyRound size={24} color="var(--primary)" />
            <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px', textTransform: 'none' }}>Change Password</h3>
          </div>

          {error && (
            <div style={{ background: '#fee2e2', color: '#b91c1c', padding: '12px', borderRadius: '8px', marginBottom: '20px', fontSize: '14px', fontWeight: '500' }}>
              {error}
            </div>
          )}

          {message && (
            <div style={{ background: '#d1fae5', color: '#047857', padding: '12px', borderRadius: '8px', marginBottom: '20px', fontSize: '14px', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={18} />
              {message}
            </div>
          )}

          <form onSubmit={handlePasswordChange}>
            <div className="form-group">
              <label>Current Password</label>
              <input 
                type="password" 
                className="form-control"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
            </div>
            
            <div className="form-group">
              <label>New Password</label>
              <input 
                type="password" 
                className="form-control"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: '24px' }}>
              <label>Confirm New Password</label>
              <input 
                type="password" 
                className="form-control"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
              Update Password
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}
