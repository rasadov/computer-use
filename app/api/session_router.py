import asyncio
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.dependencies import get_session_manager
from app.services.ai_processing_service import process_message_and_save
from app.services.session_manager import PostgresSessionManager
from app.utils.convert import convert_to_anthropic_message

router = APIRouter()
active_connections: Dict[str, WebSocket] = {}


@router.post("/sessions")
async def create_session(session_manager: PostgresSessionManager = Depends(get_session_manager)):
    session_id = await session_manager.create_session()
    return {"session_id": session_id}

@router.get("/sessions")
async def list_sessions(session_manager: PostgresSessionManager = Depends(get_session_manager)):
    sessions = await session_manager.list_sessions()
    return {"sessions": [{"id": s.id, "status": s.status, "created_at": s.created_at} for s in sessions]}

@router.get("/sessions/{session_id}")
async def get_session(session_id: str, session_manager: PostgresSessionManager = Depends(get_session_manager)):
    session = await session_manager.get_session(session_id)
    if session is None:
        return {"error": "Session not found"}
    
    messages = await session_manager.get_session_messages(session_id)
    return {
        "id": session.id,
        "status": session.status,
        "created_at": session.created_at,
        "messages": [{"role": m.role, "content": m.content} for m in messages]
    }

@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, message: dict, session_manager: PostgresSessionManager = Depends(get_session_manager)):
    print(f"Received message for session {session_id}: {message}")
    
    session = await session_manager.get_session(session_id)
    if session is None:
        print(f"Session {session_id} not found")
        return {"error": "Session not found"}
    
    try:
        print(f"Adding user message to database...")
        saved_message = await session_manager.add_message(
            session_id=session_id,
            role="user",
            content=message["content"]
        )
        print(f"User message saved successfully: {saved_message.id}")
        
        db_messages = await session_manager.get_session_messages(session_id)
        anthropic_messages = [convert_to_anthropic_message(msg) for msg in db_messages]
        
        print(f"Starting background task to process message...")
        asyncio.create_task(process_message_and_save(session_id, active_connections, anthropic_messages, session_manager))
        
        return {"status": "processing"}
        
    except Exception as e:
        print(f"Error in send_message: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to process message: {str(e)}"}

@router.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates from the agent"""
    await websocket.accept()
    active_connections[session_id] = websocket
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if session_id in active_connections:
            del active_connections[session_id]
