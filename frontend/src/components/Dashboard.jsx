import React, { useState, useEffect } from 'react';
import { getEmployees, getTodayRawLogs, pingDevice, getDeviceSettings, updateDeviceSettings, syncAttendance, deleteTodayAttendance } from '../services/api';
import { RefreshCw, Settings, Save, Trash2 } from 'lucide-react';
import { wsManager } from '../services/websocket';

export default function Dashboard() {
  const [employees, setEmployees] = useState([]);
  const [todayRawLogs, setTodayRawLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [deviceIp, setDeviceIp] = useState('10.10.10.10');
  const [isEditingIp, setIsEditingIp] = useState(false);
  const [savingIp, setSavingIp] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [empRes, logsRes, settingsRes] = await Promise.all([
        getEmployees(),
        getTodayRawLogs(),
        getDeviceSettings()
      ]);
      setEmployees(empRes.data);
      setTodayRawLogs(logsRes.data);
      setDeviceIp(settingsRes.data.ip_address || '10.10.10.10');
    } catch (error) {
      console.error("Error fetching dashboard data", error);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();

    // Subscribe to real-time events to trigger refreshes
    const unsubPunch = wsManager.subscribe('NEW_PUNCH', () => {
      fetchData();
    });

    const unsubEmp = wsManager.subscribe('NEW_EMPLOYEE', () => {
      fetchData();
    });

    const unsubUpdate = wsManager.subscribe('EMPLOYEE_UPDATED', () => {
      fetchData();
    });

    return () => {
      unsubPunch();
      unsubEmp();
      unsubUpdate();
    };
  }, []);

  const handleSaveIp = async () => {
    setSavingIp(true);
    try {
      await updateDeviceSettings({ ip_address: deviceIp });
      setIsEditingIp(false);
    } catch (error) {
      console.error("Failed to save IP", error);
    }
    setSavingIp(false);
  };

  const handleDeleteToday = async () => {
    if (!window.confirm("Are you sure you want to delete all raw punches and attendance records for today? This cannot be undone.")) {
      return;
    }
    try {
      await deleteTodayAttendance();
      fetchData();
      alert("Today's logs cleared successfully.");
    } catch (error) {
      console.error("Failed to delete today's attendance", error);
      alert("Failed to delete logs.");
    }
  };

  // We can calculate 'Present Today' by finding unique employee IDs in today's logs
  const uniquePresent = new Set(todayRawLogs.map(log => log.machine_user_id)).size;
  const absentCount = employees.length - uniquePresent;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Dashboard</h2>
          <p className="page-subtitle">Overview of today's attendance metrics</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--surface)', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <Settings size={18} color="var(--text-secondary)" />
            {isEditingIp ? (
              <input 
                type="text" 
                value={deviceIp} 
                onChange={(e) => setDeviceIp(e.target.value)}
                style={{ width: '120px', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--primary)' }}
                autoFocus
              />
            ) : (
              <span style={{ fontWeight: '500' }}>{deviceIp}</span>
            )}
            
            {isEditingIp ? (
              <button className="btn btn-primary" style={{ padding: '4px 8px' }} onClick={handleSaveIp} disabled={savingIp}>
                <Save size={16} />
              </button>
            ) : (
              <button className="btn btn-secondary" style={{ padding: '4px 8px' }} onClick={() => setIsEditingIp(true)}>
                Edit IP
              </button>
            )}
          </div>

          <button className="btn btn-danger" onClick={handleDeleteToday} disabled={isEditingIp}>
            <Trash2 size={18} />
            Delete Today's Logs
          </button>
        </div>
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <>
          <div className="dashboard-grid">
            <div className="card">
              <h3>Total Employees</h3>
              <div className="value">{employees.length}</div>
            </div>
            <div className="card">
              <h3>Present Today</h3>
              <div className="value" style={{ color: 'var(--success)' }}>{uniquePresent}</div>
            </div>
            <div className="card">
              <h3>Absent Today</h3>
              <div className="value" style={{ color: 'var(--danger)' }}>{absentCount}</div>
            </div>
          </div>
          
          <h3 style={{ marginBottom: '16px' }}>Recent Activity (Raw Punches)</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Machine ID</th>
                  <th>Punch Time</th>
                  <th>Punch Type</th>
                </tr>
              </thead>
              <tbody>
                {todayRawLogs
                  .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                  .slice(0, 10)
                  .map(log => (
                  <tr key={log.id}>
                    <td>{log.employee_name}</td>
                    <td>{log.machine_user_id}</td>
                    <td>{new Date(log.timestamp).toLocaleTimeString()}</td>
                    <td>
                      <span className="badge badge-present">
                        Punch Received
                      </span>
                    </td>
                  </tr>
                ))}
                {todayRawLogs.length === 0 && (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center' }}>No punches recorded today</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
      `}</style>
    </div>
  );
}
