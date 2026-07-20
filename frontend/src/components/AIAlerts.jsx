import React, { useState, useEffect } from 'react';
import { getAIAlerts } from '../services/api';
import { BellRing, Send, Bot, Mail } from 'lucide-react';
import { useAI } from '../context/AIContext';
import ReactMarkdown from 'react-markdown';

export default function AIAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [draftingId, setDraftingId] = useState(null);
  const [drafts, setDrafts] = useState({});
  const { status } = useAI();

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const res = await getAIAlerts();
      setAlerts(res.data.alerts || []);
    } catch (err) {
      console.error("Failed to fetch alerts", err);
    }
    setLoading(false);
  };

  const handleDraftWarning = async (emp) => {
    if (status.state !== 'ready') {
      alert("AI Assistant is not ready or not installed. Please install it from the AI Assistant tab.");
      return;
    }
    
    setDraftingId(emp.employee_id);
    setDrafts(prev => ({ ...prev, [emp.employee_id]: '' }));

    try {
      const baseUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname || '127.0.0.1'}:8080`;
      const response = await fetch(`${baseUrl}/ai/draft-warning`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: emp.employee_id,
          lates: emp.lates,
          absences: emp.absences,
          model: 'qwen2.5:0.5b'
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(l => l.trim() !== '');
        
        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.response) {
              setDrafts(prev => ({
                ...prev,
                [emp.employee_id]: (prev[emp.employee_id] || '') + data.response
              }));
            }
          } catch (e) {
            console.error("Error parsing stream chunk", e);
          }
        }
      }
    } catch (error) {
      console.error("Error generating draft", error);
      setDrafts(prev => ({
        ...prev,
        [emp.employee_id]: 'Failed to generate draft. Ensure AI is running.'
      }));
    }
    setDraftingId(null);
  };

  const handleSendEmail = (emp) => {
    if (!emp.email) {
      alert("This employee does not have an email address set! Please update their profile in the Employees tab.");
      return;
    }
    
    const draftText = drafts[emp.employee_id];
    if (!draftText) return;

    // Use mailto: scheme to open default email client
    const subject = encodeURIComponent("Important: Attendance Warning");
    const body = encodeURIComponent(draftText);
    window.location.href = `mailto:${emp.email}?subject=${subject}&body=${body}`;
  };

  return (
    <div className="alerts-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">AI Alerts</h2>
          <p className="page-subtitle">Auto-generated warnings for frequent lates and absences (Last 7 Days)</p>
        </div>
      </div>

      {loading ? (
        <p>Scanning attendance records...</p>
      ) : alerts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', background: 'var(--surface)', borderRadius: '12px' }}>
          <BellRing size={48} color="var(--text-muted)" style={{ marginBottom: '16px', opacity: 0.5 }} />
          <h3 style={{ color: 'var(--text-main)' }}>No Alerts Found</h3>
          <p style={{ color: 'var(--text-muted)' }}>All employees have good attendance records for the past 7 days!</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {alerts.map(alert => (
            <div key={alert.employee_id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-main)' }}>{alert.full_name}</h3>
                  <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {alert.department} &bull; {alert.email || <span style={{ color: 'var(--danger)' }}>No Email Set</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {alert.lates > 0 && <span className="badge badge-warning">{alert.lates} Lates</span>}
                  {alert.absences > 0 && <span className="badge badge-danger">{alert.absences} Absences</span>}
                </div>
              </div>

              {!drafts[alert.employee_id] && draftingId !== alert.employee_id && (
                <button 
                  className="btn btn-primary" 
                  style={{ alignSelf: 'flex-start', display: 'flex', gap: '8px', alignItems: 'center' }}
                  onClick={() => handleDraftWarning(alert)}
                >
                  <Bot size={16} /> Draft AI Warning
                </button>
              )}

              {draftingId === alert.employee_id && (
                <div style={{ padding: '16px', background: 'var(--background)', borderRadius: '8px', border: '1px solid var(--surface-border)' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Bot size={16} className="animate-spin" /> AI is drafting the email...
                  </p>
                </div>
              )}

              {drafts[alert.employee_id] && (
                <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
                  <div style={{ background: '#f1f5f9', padding: '10px 16px', borderBottom: '1px solid #e2e8f0', fontSize: '14px', fontWeight: '600', color: '#475569', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>Email Draft</div>
                    <button 
                      className="btn btn-primary" 
                      style={{ padding: '6px 12px', fontSize: '13px', display: 'flex', gap: '6px', alignItems: 'center' }}
                      onClick={() => handleSendEmail(alert)}
                    >
                      <Send size={14} /> Send via Email App
                    </button>
                  </div>
                  <div style={{ padding: '16px', fontSize: '14px', color: '#334155', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
                    <ReactMarkdown>{drafts[alert.employee_id]}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
