from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import asyncio
from computer_use_demo.loop import sampling_loop, APIProvider
from app.services.session_manager import session_manager
from app.config import settings

router = APIRouter(prefix="/api/v1")
active_connections: Dict[str, WebSocket] = {}


@router.post("/sessions")
async def create_session():
    session_id = await session_manager.create_session()
    return {"session_id": session_id}

@router.get("/sessions")
async def list_sessions():
    sessions = await session_manager.list_sessions()
    return {"sessions": sessions}

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = await session_manager.get_session(session_id)
    if session is None:
        return {"error": "Session not found"}
    return session

@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, message: dict):
    session = await session_manager.get_session(session_id)
    if session is None:
        return {"error": "Session not found"}
    
    # Add user message
    user_msg = {"role": "user", "content": message["content"]}
    session["messages"].append(user_msg)
    
    # Start agent processing (this will stream via websocket)
    asyncio.create_task(process_message(session_id, message["content"]))
    
    return {"status": "processing"}

@router.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket
    
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        if session_id in active_connections:
            del active_connections[session_id]

async def process_message(session_id: str, user_input: str):
    """Process user message with computer use agent"""
    session = await session_manager.get_session(session_id)
    if session is None or session_id not in active_connections:
        return
    
    websocket = active_connections[session_id]
    
    def output_callback(content):
        asyncio.create_task(websocket.send_text(json.dumps({
            "type": "assistant_message",
            "content": content
        })))
    
    def tool_callback(result, tool_id):
        asyncio.create_task(websocket.send_text(json.dumps({
            "type": "tool_result", 
            "tool_id": tool_id,
            "result": str(result)
        })))
    
    def api_callback(request, response, error):
        pass
    
    try:
        messages = await sampling_loop(
            model="claude-sonnet-4-20250514",
            provider=APIProvider.ANTHROPIC,
            system_prompt_suffix="",
            messages=session["messages"],
            output_callback=output_callback,
            tool_output_callback=tool_callback,
            api_response_callback=api_callback,
            api_key=settings.ANTHROPIC_API_KEY,
            tool_version="computer_use_20250124"
        )
        
        messages_dicts = [dict(m.__dict__) for m in messages]

        await session_manager.update_session(session_id, messages_dicts)        

    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))
