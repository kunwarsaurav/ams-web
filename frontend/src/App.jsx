import React, { useEffect, useState } from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import EmployeeList from './components/EmployeeList';
import AttendanceTable from './components/AttendanceTable';
import Settings from './components/Settings';
import AIAssistant from './components/AIAssistant';
import AIAlerts from './components/AIAlerts';
import Login from './components/Login';
import { wsManager } from './services/websocket';
import { AIProvider } from './context/AIContext';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const { isAuthenticated, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    wsManager.connect();
  }, []);

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <Router>
      <div className="app-layout">
        {/* Mobile Header */}
        <div className="mobile-header">
          <h2>Attendance</h2>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="btn-icon">
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Sidebar Overlay for mobile */}
        <div 
          className={`sidebar-overlay ${sidebarOpen ? 'open' : ''}`} 
          onClick={() => setSidebarOpen(false)} 
        />

        <Sidebar onLogout={logout} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/employees" element={<EmployeeList />} />
            <Route path="/attendance" element={<AttendanceTable />} />
            <Route path="/ai" element={<AIAssistant />} />
            <Route path="/alerts" element={<AIAlerts />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AIProvider>
        <AppContent />
      </AIProvider>
    </AuthProvider>
  );
}
