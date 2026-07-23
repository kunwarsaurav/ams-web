import React, { useState } from 'react';
import { User, KeyRound, CheckCircle2, Building, Mail, Save, Fingerprint } from 'lucide-react';
import { getDeviceSettings, updateDeviceSettings } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function Settings() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [pwdMessage, setPwdMessage] = useState('');
  const [pwdError, setPwdError] = useState('');
  const [profileMessage, setProfileMessage] = useState('');
  const [profileError, setProfileError] = useState('');
  const { login } = useAuth();

  const [companyName, setCompanyName] = useState('');
  const [hrEmail, setHrEmail] = useState('');
  const [deviceId, setDeviceId] = useState(''); // Device Serial Number

  React.useEffect(() => {
    getDeviceSettings().then(res => {
      setCompanyName(res.data.company_name || 'Synthbit Technologies');
      setHrEmail(res.data.hr_email || 'hr@synthbit.com');
      setDeviceId(res.data.device_id || '');
    }).catch(err => console.error(err));
  }, []);

  const handleCompanySave = async (e) => {
    e.preventDefault();
    try {
      await updateDeviceSettings({
        company_name: companyName,
        hr_email: hrEmail,
        device_id: deviceId
      });
      setProfileMessage('Company Profile saved successfully!');
      setTimeout(() => setProfileMessage(''), 3000);
    } catch (err) {
      setProfileError('Failed to save Company Profile');
      setTimeout(() => setProfileError(''), 3000);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPwdError('');
    setPwdMessage('');

    if (newPassword !== confirmPassword) {
      setPwdError('New passwords do not match');
      return;
    }

    if (newPassword.length < 6) {
      setPwdError('New password must be at least 6 characters');
      return;
    }

    try {
      // Verify current password by trying to log in
      await login('admin', currentPassword);
      
      await updateDeviceSettings({
        company_name: companyName,
        hr_email: hrEmail,
        device_id: deviceId,
        admin_password: newPassword
      });
      
      // Cleanup old local storage if exists
      localStorage.removeItem('adminPassword');
      
      setPwdMessage('Password changed successfully!');
      setTimeout(() => setPwdMessage(''), 3000);
      
      // Reset form
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPwdError('Current password is incorrect');
    }
  };

  return (
    <div className="settings-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Settings</h2>
          <p className="page-subtitle">Manage your account and system preferences</p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '32px', flexWrap: 'wrap' }}>
        
        {/* Left Column */}
        <div style={{ flex: '1 1 300px', display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Profile Card */}
          <div className="card">
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

            {pwdError && (
              <div style={{ background: '#fee2e2', color: '#b91c1c', padding: '12px', borderRadius: '8px', marginBottom: '20px', fontSize: '14px', fontWeight: '500' }}>
                {pwdError}
              </div>
            )}

            {pwdMessage && (
              <div style={{ background: '#d1fae5', color: '#047857', padding: '12px', borderRadius: '8px', marginBottom: '20px', fontSize: '14px', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={18} />
                {pwdMessage}
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

        {/* Right Column */}
        <div style={{ flex: '1 1 300px', display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Company Profile Card */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
              <Building size={24} color="var(--primary)" />
              <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px', textTransform: 'none' }}>Company Profile</h3>
            </div>

            {profileError && (
              <div style={{ background: '#fee2e2', color: '#b91c1c', padding: '12px', borderRadius: '8px', marginBottom: '20px', fontSize: '14px', fontWeight: '500' }}>
                {profileError}
              </div>
            )}

            {profileMessage && (
              <div style={{ background: '#d1fae5', color: '#047857', padding: '12px', borderRadius: '8px', marginBottom: '20px', fontSize: '14px', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={18} />
                {profileMessage}
              </div>
            )}

            <form onSubmit={handleCompanySave}>
              <div className="form-group">
                <label>Company Name</label>
                <div style={{ position: 'relative' }}>
                  <Building size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input 
                    type="text" 
                    className="form-control"
                    style={{ paddingLeft: '40px' }}
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="E.g. Synthbit Technologies"
                    required
                  />
                </div>
              </div>
              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label>HR Email Address</label>
                <div style={{ position: 'relative' }}>
                  <Mail size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input 
                    type="email" 
                    className="form-control"
                    style={{ paddingLeft: '40px' }}
                    value={hrEmail}
                    onChange={(e) => setHrEmail(e.target.value)}
                    placeholder="hr@company.com"
                    required
                  />
                </div>
              </div>
              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label>Device Serial Number (dev_id)</label>
                <div style={{ position: 'relative' }}>
                  <Fingerprint size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input 
                    type="text" 
                    className="form-control"
                    style={{ paddingLeft: '40px' }}
                    value={deviceId}
                    onChange={(e) => setDeviceId(e.target.value)}
                    placeholder="E.g. C26188C41B251635"
                  />
                </div>
                <small style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px', display: 'block' }}>
                  Required to link your physical attendance device to this workspace.
                </small>
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Save size={16} /> Save Profile
              </button>
            </form>
          </div>
        </div>

      </div>
    </div>
  );
}
