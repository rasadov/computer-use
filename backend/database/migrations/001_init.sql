-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) NOT NULL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(255) DEFAULT 'active',
    metadata JSON DEFAULT '{}'::json
);

-- Create chat_messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(255) NOT NULL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    content JSON NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_type VARCHAR(255) DEFAULT 'text',
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_timestamp ON chat_messages(timestamp);
CREATE INDEX IF NOT EXISTS ix_sessions_created_at ON sessions(created_at);
CREATE INDEX IF NOT EXISTS ix_sessions_status ON sessions(status);
