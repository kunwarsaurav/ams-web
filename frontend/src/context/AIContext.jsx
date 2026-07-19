import React, { createContext, useState, useEffect, useContext } from 'react';

export const AIContext = createContext();

export function AIProvider({ children }) {
  const [status, setStatus] = useState({ state: 'checking' }); // checking, setup, installing, downloading, ready
  const [downloadProgress, setDownloadProgress] = useState('');
  const API_BASE = "http://127.0.0.1:8080";

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/ai/status`);
      const data = await res.json();
      
      if (!data.installed) {
        setStatus({ state: 'setup' });
      } else if (!data.running) {
        setTimeout(checkStatus, 2000);
      } else if (data.models && data.models.length === 0) {
        setStatus({ state: 'downloading' });
        startModelPull();
      } else {
        setStatus({ state: 'ready', model: data.models[0] });
      }
    } catch (e) {
      setTimeout(checkStatus, 2000);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const installOllama = async () => {
    setStatus({ state: 'installing' });
    try {
      await fetch(`${API_BASE}/ai/setup/install`, { method: 'POST' });
      const pollInstall = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/ai/status`);
          const data = await res.json();
          if (data.installed && data.running) {
            clearInterval(pollInstall);
            setStatus({ state: 'downloading' });
            startModelPull();
          }
        } catch (e) {}
      }, 3000);
    } catch (e) {
      console.error(e);
      setStatus({ state: 'setup' });
    }
  };

  const startModelPull = async () => {
    try {
      const res = await fetch(`${API_BASE}/ai/setup/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'gemma2:9b' })
      });
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        const lines = text.split('\n').filter(l => l.trim() !== '');
        
        for (let line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.status) {
              setDownloadProgress(data.status);
            }
          } catch(e) {}
        }
      }
      setTimeout(checkStatus, 2000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <AIContext.Provider value={{ status, downloadProgress, installOllama }}>
      {children}
    </AIContext.Provider>
  );
}

export const useAI = () => useContext(AIContext);
