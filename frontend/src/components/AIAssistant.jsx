import React, { useState, useEffect, useRef } from 'react';
import { Bot, Send, Download, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { useAI } from '../context/AIContext';

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname || '127.0.0.1'}:8080`;

export default function AIAssistant() {
  const { status, downloadProgress, installOllama, messages, setMessages } = useAI();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const res = await fetch(`${API_BASE}/ai/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userMessage.content, model: status.model || 'llama3.1:8b' })
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let aiResponseText = "";
      let buffer = "";
      setMessages(prev => [...prev, { role: 'ai', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        
        if (value) {
          buffer += decoder.decode(value, { stream: true });
        }
        
        const lines = buffer.split('\n');
        // If done, we process all lines including the last one without a newline
        buffer = done ? "" : lines.pop(); 
        
        for (let line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.error) {
              aiResponseText += `\n**Error**: ${data.error}`;
              setMessages(prev => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1].content = aiResponseText;
                return newMessages;
              });
            } else if (data.detail) {
              aiResponseText += `\n**API Error**: ${typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)}`;
              setMessages(prev => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1].content = aiResponseText;
                return newMessages;
              });
            } else if (data.response) {
              aiResponseText += data.response;
              setMessages(prev => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1].content = aiResponseText;
                return newMessages;
              });
            }
          } catch(e) {}
        }
        
        if (done) break;
      }
    } catch (error) {
      console.error(error);
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].content = "Sorry, I encountered an error communicating with the local AI.";
        return newMessages;
      });
    } finally {
      setIsTyping(false);
    }
  };

  if (status.state === 'checking') {
    return (
      <div className="ai-container center-content">
        <Loader2 className="animate-spin text-primary" size={48} />
        <h2 style={{marginTop: '20px'}}>Waking up AI Engine...</h2>
      </div>
    );
  }

  if (status.state === 'setup') {
    return (
      <div className="ai-container center-content">
        <div className="glass-card setup-card">
          <div className="setup-icon-wrapper">
            <Sparkles size={48} className="text-primary" />
          </div>
          <h2>Local AI Integration</h2>
          <p>
            Supercharge your attendance management with contextual AI. 
            Your data never leaves your computer, ensuring 100% privacy and security.
          </p>
          <div className="benefits">
            <div className="benefit-item">
              <Bot size={20}/> Ask natural language queries
            </div>
            <div className="benefit-item">
              <AlertCircle size={20}/> Detect shift anomalies
            </div>
          </div>
          <button onClick={installOllama} className="btn-primary btn-large">
            <Download size={20} />
            Install AI Engine
          </button>
        </div>
      </div>
    );
  }

  if (status.state === 'installing') {
    return (
      <div className="ai-container center-content">
        <div className="glass-card setup-card text-center">
          <Loader2 className="animate-spin text-primary mx-auto mb-4" size={48} />
          <h2>Installing AI Engine</h2>
          <p className="text-muted">This will run silently in the background. Please wait...</p>
        </div>
      </div>
    );
  }

  if (status.state === 'downloading') {
    return (
      <div className="ai-container center-content">
        <div className="glass-card setup-card text-center">
          <Loader2 className="animate-spin text-primary mx-auto mb-4" size={48} />
          <h2>Downloading Model</h2>
          <p className="text-muted">Pulling required AI model (llama3.1:8b)...</p>
          {downloadProgress && (
            <div className="progress-text mt-4 p-2 bg-light rounded text-sm mb-4">
              {downloadProgress}
            </div>
          )}
          <div className="mt-4 p-3" style={{ background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', color: 'var(--primary)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
            <strong>Background Download Active</strong>
            <p style={{ margin: '8px 0 0 0', fontSize: '14px' }}>
              You can safely navigate to the Dashboard or other pages. The AI model will continue downloading silently in the background!
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Ready State - Chat UI
  return (
    <div className="ai-chat-container">
      <div className="chat-header glass-header">
        <div className="flex items-center gap-2">
          <Bot size={24} className="text-primary" />
          <h2>AI Assistant</h2>
        </div>
        <div className="model-badge">Synth1.0 AI</div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-chat-state">
            <Sparkles size={48} className="text-muted mb-4" />
            <h3>How can I help you today?</h3>
            <p>Try asking "Who was late today?" or "Summarize overtime for this week".</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`message-wrapper ${msg.role}`}>
            {msg.role === 'ai' && (
              <div className="avatar ai-avatar">
                <Bot size={20} />
              </div>
            )}
            <div className="message-bubble">
              {msg.content}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="message-wrapper ai">
            <div className="avatar ai-avatar"><Bot size={20}/></div>
            <div className="message-bubble typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="chat-input-wrapper glass-footer">
        <form onSubmit={sendMessage} className="chat-form">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about attendance, shifts, or policies..."
            disabled={isTyping}
          />
          <button type="submit" disabled={!input.trim() || isTyping} className="send-btn">
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}
