import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Play, 
  Square, 
  Camera, 
  Settings, 
  Send, 
  Plus, 
  Monitor, 
  MessageSquare, 
  ChevronDown,
  ChevronRight,
  Circle,
  User,
  Bot,
} from 'lucide-react';

const ComputerUseInterface = () => {
  // State management
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [screenshot, setScreenshot] = useState(null);

  // Configuration state
  const [config, setConfig] = useState({
    model: 'claude-opus-4-1-20250805',
    apiProvider: 'anthropic',
    maxTokens: 4096,
    thinkingBudget: null,
    systemPromptSuffix: '',
    toolVersion: 'computer_use_20250124',
    maxRetries: 3
  });

  // WebSocket ref
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  // API Base URL
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1';

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch sessions
  const fetchSessions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/sessions`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  }, [API_BASE]);

  // Create new session
  const createSession = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        await fetchSessions();
        setCurrentSession(data.session_id);
        setMessages([]);
        setError(null);
      }
    } catch (err) {
      setError('Failed to create session');
    } finally {
      setLoading(false);
    }
  };

  // Connect to WebSocket
  const connectWebSocket = useCallback((sessionId) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE}/sessions/${sessionId}/ws`);
    
    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'connection_established':
            console.log('WebSocket connected:', data.content);
            break;
          case 'assistant_message':
            setMessages(prev => [...prev, {
              id: Date.now(),
              role: 'assistant',
              content: data.content,
              timestamp: new Date()
            }]);
            break;
          case 'tool_result':
            if (data.content.base64_image) {
              setScreenshot(`data:image/png;base64,${data.content.base64_image}`);
            }
            break;
          case 'task_complete':
            setIsSessionActive(false);
            break;
          case 'error':
            setError(data.content);
            setIsSessionActive(false);
            break;
          default:
            console.log('Unknown message type:', data);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsSessionActive(false);
    };

    ws.onerror = (err) => {
      setError('WebSocket connection failed');
      setIsConnected(false);
    };

    wsRef.current = ws;
  }, [WS_BASE]);

  // Select session
  const selectSession = async (sessionId) => {
    setCurrentSession(sessionId);
    setMessages([]);
    
    try {
      const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages.map(msg => ({
          id: Date.now() + Math.random(),
          role: msg.role,
          content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
          timestamp: new Date()
        })));
      }
    } catch (err) {
      console.error('Failed to fetch session messages:', err);
    }

    connectWebSocket(sessionId);
  };

  // Send message
  const sendMessage = async () => {
    if (!messageInput.trim() || !currentSession || !isConnected) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: messageInput,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsSessionActive(true);

    try {
      const response = await fetch(`${API_BASE}/sessions/${currentSession}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSession,
          message: messageInput,
          ...config
        })
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      setMessageInput('');
      setError(null);
    } catch (err) {
      setError('Failed to send message');
      setIsSessionActive(false);
    }
  };

  // Initialize
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getSessionStatus = (session) => {
    if (session.id === currentSession && isConnected) {
      return isSessionActive ? 'active' : 'connected';
    }
    return 'idle';
  };

  const StatusIndicator = ({ status }) => {
    const colors = {
      active: 'text-green-500',
      connected: 'text-blue-500',
      idle: 'text-gray-400'
    };
    
    return <Circle className={`w-3 h-3 ${colors[status]} fill-current`} />;
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Left Sidebar - Session Management */}
      <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <button
            onClick={createSession}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Session
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-medium text-gray-400 mb-3">Active Sessions</h3>
            {sessions.length === 0 ? (
              <p className="text-gray-500 text-sm">No sessions yet</p>
            ) : (
              <div className="space-y-2">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => selectSession(session.id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      currentSession === session.id
                        ? 'bg-blue-600 border-blue-500'
                        : 'bg-gray-700 border-gray-600 hover:bg-gray-600'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium truncate">
                        Session {session.id.slice(0, 8)}
                      </span>
                      <StatusIndicator status={getSessionStatus(session)} />
                    </div>
                    <div className="text-xs text-gray-400">
                      Created: {new Date(session.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Main Content */}
        <div className="flex-1 flex">
          {/* Desktop View Area */}
          <div className="flex-1 bg-gray-900 p-6">
            <div className="col-6 p-0">
                <iframe id="vnc" src="http://localhost:6080/vnc.html?autoconnect=1&resize=scale" 
                        className="w-full h-[100vh] border-0"></iframe>
            </div>
          </div>

          {/* Right Chat Panel */}
          <div className="w-96 bg-gray-800 border-l border-gray-700 flex flex-col">
          <div className="h-16 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Monitor className="w-6 h-6 text-blue-500" />
            <h1 className="text-xl font-semibold">Computer Use Interface</h1>
          </div>
          
          <div className="flex items-center gap-4">
            {currentSession && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
                <StatusIndicator status={isConnected ? (isSessionActive ? 'active' : 'connected') : 'idle'} />
              </div>
            )}
            
            {/* <button className="p-2 hover:bg-gray-700 rounded-lg transition-colors">
              <Settings className="w-5 h-5" />
            </button> */}
          </div>
        </div>
            {/* Chat Header */}
            <div className="p-4 border-b border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Advanced Settings
                </h3>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  {showAdvanced ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </button>
              </div>

              {/* Model Selection */}
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Model</label>
                  <select
                    value={config.model}
                    onChange={(e) => setConfig(prev => ({ ...prev, model: e.target.value }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                  >
                    <option value="claude-opus-4-1-20250805">Claude Opus 4.1</option>
                    <option value="claude-opus-4-20250514">Claude Opus 4</option>
                    <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
                    <option value="claude-3-7-sonnet-20250219">Claude 3.7 Sonnet</option>
                    <option value="claude-3-5-haiku-20241022">Claude 3.5 Haiku</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">API Provider</label>
                  <select
                    value={config.apiProvider}
                    onChange={(e) => setConfig(prev => ({ ...prev, apiProvider: e.target.value }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                  >
                    <option value="anthropic">Anthropic</option>
                    <option value="bedrock">AWS Bedrock</option>
                    <option value="vertex">Google Vertex</option>
                  </select>
                </div>
              </div>

              {/* Advanced Options */}
              {showAdvanced && (
                <div className="mt-4 space-y-3 pt-4 border-t border-gray-600">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Max Tokens: {config.maxTokens}
                    </label>
                    <input
                      type="range"
                      min="1024"
                      max="8192"
                      step="256"
                      value={config.maxTokens}
                      onChange={(e) => setConfig(prev => ({ ...prev, maxTokens: parseInt(e.target.value) }))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Thinking Budget</label>
                    <input
                      type="number"
                      value={config.thinkingBudget || ''}
                      onChange={(e) => setConfig(prev => ({ ...prev, thinkingBudget: e.target.value ? parseInt(e.target.value) : null }))}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                      placeholder="Optional"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-400 mb-1">System Prompt Suffix</label>
                    <textarea
                      value={config.systemPromptSuffix}
                      onChange={(e) => setConfig(prev => ({ ...prev, systemPromptSuffix: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm h-20 resize-none"
                      placeholder="Additional system instructions..."
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Tool Version</label>
                    <select
                      value={config.toolVersion}
                      onChange={(e) => setConfig(prev => ({ ...prev, toolVersion: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                    >
                      <option value="computer_use_20250124">2025-01-24</option>
                      <option value="computer_use_20241022">2024-10-22</option>
                      <option value="computer_use_20250429">2025-04-29</option>
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 max-h-[calc(100vh-12rem)]">
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 mt-8">
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No messages yet</p>
                  <p className="text-sm mt-1">Send a message to start the conversation</p>
                </div>
              ) : (
                <div className="space-y-4 overflow-y-auto">
                  {messages.map((message) => (
                    <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`flex my-5 gap-3 p-6 max-w-[85%] ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          message.role === 'user' ? 'bg-blue-600' : 'bg-purple-600'
                        }`}>
                          {message.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                        </div>
                        <div className={`rounded-lg my-5 px-4 py-3 ${
                          message.role === 'user' 
                            ? 'bg-blue-600 text-white' 
                            : 'bg-gray-700 text-gray-100'
                        }`}>
                          <div className="text-sm whitespace-pre-wrap break-words">
                            {typeof message.content === 'string' ? message.content : JSON.stringify(message.content, null, 2)}
                          </div>
                          <div className={`text-xs my-5 ${
                            message.role === 'user' ? 'text-blue-200' : 'text-gray-400'
                          }`}>
                            {formatTimestamp(message.timestamp)}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Message Input */}
            <div className="p-4 border-t border-gray-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  placeholder={currentSession ? "Type a message..." : "Select a session first"}
                  disabled={!currentSession || !isConnected || isSessionActive}
                  className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500 disabled:opacity-50"
                />
                <button
                  onClick={sendMessage}
                  disabled={!messageInput.trim() || !currentSession || !isConnected || isSessionActive}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              
              {currentSession && !isConnected && (
                <p className="text-red-400 text-xs mt-2">Disconnected from session</p>
              )}
              
              {isSessionActive && (
                <p className="text-yellow-400 text-xs mt-2">AI is processing...</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComputerUseInterface;