from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import asyncio
from computer_use_demo.loop import sampling_loop, APIProvider
from app.services.session_manager import session_manager
from app.config import settings
from anthropic.types.beta import BetaContentBlockParam, BetaTextBlockParam

router = APIRouter()
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
    
    # Add user message in the correct format
    user_msg = {
        "role": "user", 
        "content": [{"type": "text", "text": message["content"]}]
    }
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
            await websocket.receive_text()
    except WebSocketDisconnect:
        if session_id in active_connections:
            del active_connections[session_id]

def convert_message_to_dict(message):
    """Convert anthropic message objects to serializable dictionaries"""
    if hasattr(message, '__dict__'):
        # This is an anthropic object, convert it
        result = {}
        for key, value in message.__dict__.items():
            if key.startswith('_'):
                continue
            if hasattr(value, '__dict__'):
                result[key] = convert_message_to_dict(value)
            elif isinstance(value, list):
                result[key] = [convert_message_to_dict(item) if hasattr(item, '__dict__') else item for item in value]
            else:
                result[key] = value
        return result
    elif isinstance(message, dict):
        return message
    else:
        return str(message)

async def send_websocket_message(websocket: WebSocket, message_type: str, content):
    """Safely send a message via websocket"""
    try:
        await websocket.send_text(json.dumps({
            "type": message_type,
            "content": content
        }))
    except Exception as e:
        print(f"Error sending websocket message: {e}")

async def process_message(session_id: str, user_input: str):
    """Process user message with computer use agent"""
    session = await session_manager.get_session(session_id)
    if session is None or session_id not in active_connections:
        return
    
    websocket = active_connections[session_id]
    
    def output_callback(content: BetaContentBlockParam):
        """Handle assistant output"""
        if isinstance(content, dict):
            content_dict = content
        else:
            content_dict = convert_message_to_dict(content)
        
        asyncio.create_task(send_websocket_message(
            websocket, "assistant_message", content_dict
        ))
    
    def tool_callback(result, tool_id):
        """Handle tool results"""
        # Convert ToolResult to dict
        result_dict = {}
        if hasattr(result, 'output') and result.output:
            result_dict['output'] = result.output
        if hasattr(result, 'error') and result.error:
            result_dict['error'] = result.error
        if hasattr(result, 'base64_image') and result.base64_image:
            result_dict['base64_image'] = result.base64_image
        if hasattr(result, 'system') and result.system:
            result_dict['system'] = result.system
            
        asyncio.create_task(send_websocket_message(
            websocket, "tool_result", json.dumps(result_dict)
        ))
    
    def api_callback(request, response, error):
        """We will add this as http logs to chat later"""
        if error:
            print(f"API Error: {error}")
    
    try:
        # Run the sampling loop
        updated_messages = await sampling_loop(
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
        
        # Convert all messages to serializable format
        serializable_messages = []
        for msg in updated_messages:
            serializable_messages.append(convert_message_to_dict(msg))

        # Update session with converted messages
        await session_manager.update_session(session_id, serializable_messages)
        
        # Send completion signal
        await send_websocket_message(websocket, "task_complete", "Task completed successfully")

    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        print(error_msg)
        await send_websocket_message(websocket, "error", error_msg)