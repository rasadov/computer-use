# Computer Use Demo API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
No authentication required for this demo.

---

## REST API Endpoints

### 1. Create New Session
**Endpoint:** `POST /api/v1/sessions`

**Description:** Creates a new agent task session.

**Request:**
```http
POST /api/v1/sessions
Content-Type: application/json
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Frontend Usage:**
```javascript
const res = await fetch('/api/v1/sessions', { method: 'POST' });
const data = await res.json();
currentSession = data.session_id;
```

---

### 2. List All Sessions
**Endpoint:** `GET /api/v1/sessions`

**Description:** Retrieves all available sessions with their metadata.

**Request:**
```http
GET /api/v1/sessions
```

**Response:**
```json
{
  "sessions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "active",
      "created_at": "2025-01-27T10:30:00Z",
      "is_connected": true
    },
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "status": "inactive", 
      "created_at": "2025-01-27T09:15:00Z",
      "is_connected": false
    }
  ]
}
```

**Frontend Usage:**
```javascript
const res = await fetch('/api/v1/sessions');
const data = await res.json();
// Renders session list in left panel
```

---

### 3. Get Session Details
**Endpoint:** `GET /api/v1/sessions/{session_id}`

**Description:** Retrieves detailed information about a specific session including message history.

**Request:**
```http
GET /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "created_at": "2025-01-27T10:30:00Z",
  "is_connected": true,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Search the weather in Dubai"
        }
      ]
    },
    {
      "role": "assistant", 
      "content": [
        {
          "type": "text",
          "text": "I'll help you search for the weather in Dubai. Let me open Firefox and search for that information."
        },
        {
          "type": "tool_use",
          "id": "toolu_abc123",
          "name": "computer",
          "input": {
            "action": "screenshot"
          }
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_abc123",
          "content": [
            {
              "type": "image",
              "source": {
                "type": "base64",
                "media_type": "image/png", 
                "data": "iVBORw0KGgoAAAANSUhEUgAA..."
              }
            }
          ]
        }
      ]
    }
  ]
}
```

**Frontend Usage:**
```javascript
const res = await fetch(`/api/v1/sessions/${sessionId}`);
const sessionData = await res.json();
// Loads and displays message history
```

---

### 4. Send Message to Session
**Endpoint:** `POST /api/v1/sessions/{session_id}/messages`

**Description:** Sends a user message to Claude and triggers AI processing.

**Request:**
```http
POST /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/messages
Content-Type: application/json

{
  "content": {
    "type": "text",
    "text": "Search the weather in San Francisco"
  }
}
```

**Response:**
```json
{
  "status": "processing"
}
```

**Frontend Usage:**
```javascript
const messageContent = {
    type: "text",
    text: message
};

const response = await fetch(`/api/v1/sessions/${currentSession}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: messageContent })
});
```

---

## WebSocket API

### WebSocket Connection
**Endpoint:** `ws://localhost:8000/api/v1/sessions/{session_id}/ws`

**Description:** Establishes real-time connection for streaming AI responses and tool execution results.

**Frontend Usage:**
```javascript
const wsUrl = `ws://localhost:8000/api/v1/sessions/${currentSession}/ws`;
ws = new WebSocket(wsUrl);
```

---

### WebSocket Message Types

#### 1. Connection Established
**Type:** `connection_established`

**Description:** Sent when WebSocket connection is successfully established.

```json
{
  "type": "connection_established",
  "content": "Connected to session 550e8400-e29b-41d4-a716-446655440000"
}
```

#### 2. Assistant Message
**Type:** `assistant_message`

**Description:** Streams Claude's text responses in real-time.

```json
{
  "type": "assistant_message",
  "content": {
    "type": "text",
    "text": "I'll help you search for the weather in Dubai."
  }
}
```

**Complex Assistant Message (Tool Use):**
```json
{
  "type": "assistant_message",
  "content": {
    "type": "tool_use",
    "id": "toolu_abc123",
    "name": "computer",
    "input": {
      "action": "screenshot"
    }
  }
}
```

#### 3. Tool Result
**Type:** `tool_result`

**Description:** Streams results from tool execution (screenshots, command outputs, etc.).

**Screenshot Result:**
```json
{
  "type": "tool_result",
  "content": {
    "base64_image": "iVBORw0KGgoAAAANSUhEUgAA...",
    "output": "Screenshot taken successfully"
  },
  "tool_id": "toolu_abc123"
}
```

**Command Output Result:**
```json
{
  "type": "tool_result", 
  "content": {
    "output": "Firefox launched successfully",
    "error": null
  },
  "tool_id": "toolu_def456"
}
```

#### 4. Task Complete
**Type:** `task_complete`

**Description:** Indicates that the AI has completed processing the user's request.

```json
{
  "type": "task_complete",
  "content": "Task completed successfully. Saved 3 new messages."
}
```

#### 5. Status Update
**Type:** `status`

**Description:** Provides status updates during processing.

```json
{
  "type": "status",
  "content": "Processing task..."
}
```

#### 6. Error
**Type:** `error`

**Description:** Reports errors during processing.

```json
{
  "type": "error",
  "content": "Failed to execute tool: Screenshot command timed out"
}
```

#### 7. Debug (Development)
**Type:** `debug`

**Description:** Debug information (may be present in development mode).

```json
{
  "type": "debug",
  "content": "Starting sampling loop with 2 messages"
}
```

---

## Data Models

### Message Content Types

#### Text Content
```json
{
  "type": "text",
  "text": "Your message here"
}
```

#### Tool Use Content
```json
{
  "type": "tool_use",
  "id": "toolu_abc123",
  "name": "computer",
  "input": {
    "action": "screenshot"
  }
}
```

#### Tool Result Content
```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_abc123",
  "content": [
    {
      "type": "image",
      "source": {
        "type": "base64",
        "media_type": "image/png",
        "data": "iVBORw0KGgoAAAANSUhEUgAA..."
      }
    }
  ]
}
```

---

## Frontend Integration Examples

### Complete Message Flow

1. **User sends message:**
```javascript
// User types "Search weather in Dubai"
const messageContent = {
    type: "text", 
    text: "Search weather in Dubai"
};

// Send to backend
await fetch(`/api/v1/sessions/${currentSession}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: messageContent })
});
```

2. **Backend processes and streams responses via WebSocket:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'assistant_message':
            if (data.content.type === 'text') {
                addMessage('assistant', data.content.text);
            } else if (data.content.type === 'tool_use') {
                addToolUse(data.content);
            }
            break;
            
        case 'tool_result':
            if (data.content.base64_image) {
                displayScreenshot(data.content.base64_image);
            }
            if (data.content.output) {
                displayToolOutput(data.content.output);
            }
            break;
            
        case 'task_complete':
            enableInput();
            updateStatus('Task completed');
            break;
    }
};
```

### Error Handling

```javascript
// HTTP Error Handling
try {
    const response = await fetch('/api/v1/sessions', { method: 'POST' });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
} catch (error) {
    updateStatus('Error: ' + error.message, 'error');
}

// WebSocket Error Handling
ws.onerror = (error) => {
    updateStatus('WebSocket error', 'error');
    console.error('WebSocket error:', error);
};
```

---

## Health Check Endpoints

### Redis Health Check
**Endpoint:** `GET /api/v1/sessions/health/redis`

**Description:** Checks Redis connection status and active sessions.

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 2,
  "sessions": [
    "550e8400-e29b-41d4-a716-446655440000",
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
  ]
}
```

---

## Error Codes

| HTTP Status | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid message format |
| 404 | Session not found |
| 500 | Internal server error |
| 502 | Bad Gateway - AI service unavailable |

## Rate Limits

No rate limits are currently enforced in this demo implementation.

---