let currentSession = null;
let ws = null;
let isProcessing = false;

// Create new session
document.getElementById('newSession').onclick = async () => {
    try {
        updateStatus('Creating new session...');
        const res = await fetch('/api/v1/sessions', { method: 'POST' });
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        const data = await res.json();
        if (!data.session_id) {
            throw new Error('No session ID returned');
        }
        
        currentSession = data.session_id;
        connectWebSocket();
        loadSessions();
        clearMessages();
        enableInput();
        updateStatus('Session created successfully');
    } catch (error) {
        console.error('Error creating session:', error);
        updateStatus('Error creating session: ' + error.message, 'error');
    }
};

// Connect WebSocket
function connectWebSocket() {
    if (ws) ws.close();
    
    const wsUrl = `ws://localhost:8000/api/v1/sessions/${currentSession}/ws`;
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        updateSessionStatus('active');
        updateStatus('Connected to session');
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };
    
    ws.onclose = () => {
        updateSessionStatus('inactive');
        updateStatus('Disconnected from session');
    };
    
    ws.onerror = (error) => {
        updateStatus('WebSocket error', 'error');
        console.error('WebSocket error:', error);
    };
}

// Handle different types of WebSocket messages
function handleWebSocketMessage(data) {
    console.log('WebSocket message:', data);
    
    switch (data.type) {
        case 'connection_established':
            updateStatus('Connected to session: ' + data.session_id);
            break;
        case 'task_started':
            updateStatus('Task started: ' + data.content);
            break;
        case 'assistant_message':
            addAssistantMessage(data.content);
            break;
        case 'tool_result':
            // data.content should be the tool result object directly
            addToolResult(data.content, data.tool_id);
            break;
        case 'task_complete':
            addMessage('system', data.content, 'bg-success text-white');
            isProcessing = false;
            enableInput();
            updateSessionStatus('active');
            updateStatus('Task completed');
            break;
        case 'status':
            updateStatus(data.content);
            break;
        case 'error':
            addErrorMessage(data.content);
            isProcessing = false;
            enableInput();
            updateSessionStatus('active');
            break;
        case 'heartbeat':
            // Keep connection alive
            break;
        default:
            console.log('Unknown message type:', data.type, data);
    }
}

// Send message
document.getElementById('sendBtn').onclick = async () => {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message || !currentSession || isProcessing) return;
    
    addUserMessage(message);
    input.value = '';
    disableInput();
    isProcessing = true;
    updateSessionStatus('processing');
    
    try {
        const response = await fetch(`/api/v1/sessions/${currentSession}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: message })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        updateStatus('Processing task...');
    } catch (error) {
        addErrorMessage('Failed to send message: ' + error.message);
        isProcessing = false;
        enableInput();
        updateSessionStatus('active');
    }
};

// Add different types of messages
function addUserMessage(content) {
    // Handle user messages that might be objects or strings
    let textContent = '';
    
    if (typeof content === 'string') {
        textContent = content;
    } else if (Array.isArray(content)) {
        // Extract text from content array
        textContent = content.map(item => {
            if (typeof item === 'string') return item;
            if (item.type === 'text') return item.text;
            if (item.text) return item.text;
            return JSON.stringify(item);
        }).join(' ');
    } else if (content && typeof content === 'object') {
        if (content.type === 'text') {
            textContent = content.text;
        } else if (content.text) {
            textContent = content.text;
        } else {
            textContent = JSON.stringify(content);
        }
    } else {
        textContent = String(content);
    }
    
    addMessage('user', textContent, 'user-message');
}

function addAssistantMessage(content) {
    if (typeof content === 'string') {
        addMessage('assistant', content, 'assistant-message');
    } else if (content && typeof content === 'object') {
        // Handle structured content
        if (content.type === 'text') {
            addMessage('assistant', content.text, 'assistant-message');
        } else if (content.type === 'tool_use') {
            addToolUse(content);
        } else {
            // Try to extract text content from complex objects
            let textContent = '';
            if (content.text) {
                textContent = content.text;
            } else if (content.content) {
                textContent = content.content;
            } else {
                textContent = JSON.stringify(content, null, 2);
            }
            addMessage('assistant', textContent, 'assistant-message');
        }
    }
    
    isProcessing = false;
    enableInput();
    updateSessionStatus('active');
}

function addToolUse(toolData) {
    const messages = document.getElementById('messages');
    const container = document.createElement('div');
    container.className = 'message-container';
    
    // Create header
    const header = document.createElement('div');
    header.className = 'message-header tool-header';
    header.textContent = `🔧 Tool Use: ${toolData.name || 'Unknown Tool'}`;
    
    // Create content
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const toolInput = JSON.stringify(toolData.input || {}, null, 2);
    content.innerHTML = `<pre class="mb-0 small">${toolInput}</pre>`;
    
    container.appendChild(header);
    container.appendChild(content);
    messages.appendChild(container);
    messages.scrollTop = messages.scrollHeight;
}

function addToolResult(result, toolId) {
    const messages = document.getElementById('messages');
    const container = document.createElement('div');
    container.className = 'message-container';
    
    // Create header
    const header = document.createElement('div');
    header.className = 'message-header tool-header';
    header.textContent = '🔨 Tool Result';
    
    // Create content
    const content = document.createElement('div');
    content.className = 'message-content';
    
    let hasImage = false;
    
    try {
        // Handle different result formats
        let parsed = result;
        if (typeof result === 'string') {
            try {
                parsed = JSON.parse(result);
            } catch {
                parsed = { output: result };
            }
        }
        
        // Check for images in various formats
        if (parsed.base64_image) {
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${parsed.base64_image}`;
            img.className = 'message-image';
            img.alt = 'Screenshot';
            img.style.maxWidth = '100%';
            img.style.height = 'auto';
            img.style.borderRadius = '4px';
            content.appendChild(img);
            hasImage = true;
        } else if (parsed.content && Array.isArray(parsed.content)) {
            // Handle tool_result content format
            for (const item of parsed.content) {
                if (item.type === 'image' && item.source && item.source.data) {
                    const img = document.createElement('img');
                    img.src = `data:${item.source.media_type || 'image/png'};base64,${item.source.data}`;
                    img.className = 'message-image';
                    img.alt = 'Screenshot';
                    img.style.maxWidth = '100%';
                    img.style.height = 'auto';
                    img.style.borderRadius = '4px';
                    content.appendChild(img);
                    hasImage = true;
                    break;
                } else if (item.type === 'text') {
                    const textDiv = document.createElement('div');
                    textDiv.textContent = item.text;
                    content.appendChild(textDiv);
                }
            }
        }
        
        // If no image found, show text content
        if (!hasImage) {
            let textContent = '';
            if (parsed.output) {
                textContent = parsed.output;
            } else if (parsed.error) {
                textContent = `Error: ${parsed.error}`;
                content.classList.add('text-danger');
            } else if (typeof parsed === 'string') {
                textContent = parsed;
            } else {
                textContent = JSON.stringify(parsed, null, 2);
            }
            
            const pre = document.createElement('pre');
            pre.className = 'mb-0';
            pre.textContent = textContent;
            content.appendChild(pre);
        }
        
    } catch (error) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'text-danger';
        errorDiv.textContent = `Error parsing result: ${error.message}`;
        content.appendChild(errorDiv);
    }
    
    container.appendChild(header);
    container.appendChild(content);
    messages.appendChild(container);
    messages.scrollTop = messages.scrollHeight;
}

function addErrorMessage(message) {
    addMessage('error', message, 'error-message');
}

function addMessage(type, content, className) {
    const messages = document.getElementById('messages');
    const container = document.createElement('div');
    container.className = 'message-container';
    
    // Create header
    const header = document.createElement('div');
    header.className = 'message-header';
    
    let headerText = '';
    let headerClass = '';
    
    switch (type) {
        case 'user':
            headerText = '👤 User';
            headerClass = 'user-header';
            break;
        case 'assistant':
            headerText = '🤖 Assistant';
            headerClass = 'assistant-header';
            break;
        case 'tool':
            headerText = '🔧 Tool';
            headerClass = 'tool-header';
            break;
        case 'system':
            headerText = '⚙️ System';
            headerClass = 'tool-header';
            break;
        case 'error':
            headerText = '❌ Error';
            headerClass = 'bg-danger text-white';
            break;
        default:
            headerText = type.charAt(0).toUpperCase() + type.slice(1);
    }
    
    header.textContent = headerText;
    header.className += ' ' + headerClass;
    
    // Create content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (type === 'error') {
        contentDiv.innerHTML = `<strong>Error:</strong><br>${content}`;
        contentDiv.className += ' text-danger';
    } else {
        contentDiv.textContent = content;
    }
    
    container.appendChild(header);
    container.appendChild(contentDiv);
    messages.appendChild(container);
    messages.scrollTop = messages.scrollHeight;
}

function clearMessages() {
    document.getElementById('messages').innerHTML = '';
}

function enableInput() {
    document.getElementById('messageInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('inputStatus').textContent = 'Ready to send message';
}

function disableInput() {
    document.getElementById('messageInput').disabled = true;
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('inputStatus').textContent = 'Processing...';
}

function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `mt-2 small ${type === 'error' ? 'text-danger' : 'text-muted'}`;
}

function updateSessionStatus(status) {
    const indicator = document.getElementById('sessionStatus');
    indicator.className = `status-indicator status-${status}`;
}

// Load sessions
async function loadSessions() {
    try {
        const res = await fetch('/api/v1/sessions');
        const data = await res.json();
        const sessionsDiv = document.getElementById('sessions');
        
        if (data.sessions && data.sessions.length > 0) {
            sessionsDiv.innerHTML = data.sessions.map(s => {
                const isActive = s.id === currentSession;
                const messageCount = s.messages ? s.messages.length : 0;
                return `
                    <div class="session-item p-2 border rounded mb-1 ${isActive ? 'active' : ''}" 
                         onclick="selectSession('${s.id}')">
                        <div class="d-flex justify-content-between">
                            <span>${s.id.slice(0,8)}...</span>
                            <small class="text-muted">${messageCount} msgs</small>
                        </div>
                        <small class="text-muted">${new Date(s.created_at).toLocaleTimeString()}</small>
                    </div>
                `;
            }).join('');
        } else {
            sessionsDiv.innerHTML = '<div class="text-muted text-center">No sessions yet</div>';
        }
    } catch (error) {
        updateStatus('Error loading sessions: ' + error.message, 'error');
    }
}

// Select session
async function selectSession(sessionId) {
    if (sessionId === currentSession) return;
    
    currentSession = sessionId;
    connectWebSocket();
    loadSessions();
    
    try {
        // Load session messages
        const res = await fetch(`/api/v1/sessions/${sessionId}`);
        const sessionData = await res.json();
        
        clearMessages();
        
        if (sessionData.messages && sessionData.messages.length > 0) {
            sessionData.messages.forEach(msg => {
                if (msg.role === 'user') {
                    // Handle user messages
                    if (Array.isArray(msg.content)) {
                        msg.content.forEach(contentItem => {
                            if (contentItem.type === 'text') {
                                addUserMessage(contentItem.text);
                            } else if (contentItem.type === 'tool_result') {
                                // This is actually a tool result, parse it properly
                                let toolContent = contentItem.content;
                                
                                // If content is an array (which it usually is for tool results)
                                if (Array.isArray(toolContent)) {
                                    toolContent.forEach(item => {
                                        if (item.type === 'image' && item.source) {
                                            // Create the tool result object with proper image format
                                            const imageResult = {
                                                base64_image: item.source.data,
                                                output: ''
                                            };
                                            addToolResult(imageResult, contentItem.tool_use_id);
                                        } else if (item.type === 'text') {
                                            addToolResult({ output: item.text }, contentItem.tool_use_id);
                                        }
                                    });
                                } else {
                                    addToolResult(toolContent, contentItem.tool_use_id);
                                }
                            }
                        });
                    } else if (typeof msg.content === 'string') {
                        addUserMessage(msg.content);
                    } else if (msg.content && msg.content.text) {
                        addUserMessage(msg.content.text);
                    }
                } else if (msg.role === 'assistant') {
                    // Handle assistant messages
                    if (Array.isArray(msg.content)) {
                        msg.content.forEach(contentItem => {
                            if (contentItem.type === 'text') {
                                addMessage('assistant', contentItem.text, 'assistant-message');
                            } else if (contentItem.type === 'tool_use') {
                                addToolUse(contentItem);
                            } else {
                                addAssistantMessage(contentItem);
                            }
                        });
                    } else {
                        addAssistantMessage(msg.content);
                    }
                }
            });
        }
        
        enableInput();
        updateStatus('Session loaded successfully');
    } catch (error) {
        updateStatus('Error loading session: ' + error.message, 'error');
    }
}

// Enter key support
document.getElementById('messageInput').onkeypress = (e) => {
    if (e.key === 'Enter' && !document.getElementById('sendBtn').disabled) {
        document.getElementById('sendBtn').click();
    }
};

// Initialize
loadSessions();
updateStatus('Click "Start New Agent Task" to begin');