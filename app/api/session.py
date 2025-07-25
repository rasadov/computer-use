from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict
import json
import asyncio
from app.models.message import ChatMessage
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from computer_use_demo.loop import sampling_loop, APIProvider
from app.dependencies import get_db, get_session_manager
from app.config import settings
from anthropic.types.beta import BetaContentBlockParam, BetaMessageParam, BetaTextBlockParam
from app.services.session_manager import PostgresSessionManager

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
    
    # Get messages for this session
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
        # Add user message to database
        print(f"Adding user message to database...")
        saved_message = await session_manager.add_message(
            session_id=session_id,
            role="user",
            content=message["content"]
        )
        print(f"User message saved successfully: {saved_message.id}")
        
    except Exception as e:
        print(f"Error saving user message: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to save message: {str(e)}"}
    
    # Start agent processing (this will stream via websocket)
    print(f"Starting background task to process message...")
    asyncio.create_task(process_message(session_id))
    
    return {"status": "processing"}

@router.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates from the agent"""
    await websocket.accept()
    active_connections[session_id] = websocket
    
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        if session_id in active_connections:
            del active_connections[session_id]

async def send_websocket_message(websocket: WebSocket, message_type: str, content):
    """Safely send a message via websocket"""
    try:
        await websocket.send_text(json.dumps({
            "type": message_type,
            "content": content
        }))
    except Exception as e:
        print(f"Error sending websocket message: {e}")

def convert_to_anthropic_message(db_message: ChatMessage) -> BetaMessageParam | dict:
    """Convert database message to Anthropic API format"""
    if isinstance(db_message.content, str):
        try:
            # Try to parse as JSON first (for complex messages)
            content_data = json.loads(db_message.content)
            return {
                "role": db_message.role,
                "content": content_data
            }
        except (json.JSONDecodeError, TypeError):
            # Fallback to simple text
            return {
                "role": db_message.role,
                "content": [BetaTextBlockParam(type="text", text=db_message.content)]
            }
    else:
        # JSON content (for complex messages)
        return {
            "role": db_message.role,
            "content": db_message.content if isinstance(db_message.content, list) else [db_message.content]
        }

async def process_message(session_id: str):
    """Process user message with computer use agent"""
    session_manager: PostgresSessionManager
    async for db in get_db():
        session_manager = PostgresSessionManager(
            session_repository=SessionRepository(db),
            message_repository=MessageRepository(db)
        )
        break
    
    try:
        session = await session_manager.get_session(session_id)
        if session is None:
            print(f"Session {session_id} not found in database")
            return
            
        if session_id not in active_connections:
            print(f"No websocket connection for session {session_id}")
            return
            
        websocket = active_connections[session_id]
        
        # Get all messages for this session and convert to Anthropic format
        print(f"Fetching existing messages for session {session_id}")
        db_messages = await session_manager.get_session_messages(session_id)
        print(f"Found {len(db_messages)} existing messages in database")
        
        # Store the original count to identify new messages later
        original_message_count = len(db_messages)
        
        anthropic_messages = [convert_to_anthropic_message(msg) for msg in db_messages]
        
        print(f"Processing {len(anthropic_messages)} messages for session {session_id}")
        
        # Send debug info to client
        await send_websocket_message(websocket, "debug", f"Starting processing with {len(anthropic_messages)} messages")
    
        def output_callback(content: BetaContentBlockParam):
            """Handle assistant output"""
            print(f"Output callback received: {content}")
            if hasattr(content, 'model_dump'):
                content_dict = content.model_dump()
            elif isinstance(content, dict):
                content_dict = content
            else:
                content_dict = {"type": "text", "text": str(content)}
            
            asyncio.create_task(send_websocket_message(
                websocket, "assistant_message", content_dict
            ))
        
        def tool_callback(result, tool_id):
            """Handle tool results"""
            print(f"Tool callback - ID: {tool_id}, Result: {result}")
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
                websocket, "tool_result", result_dict
            ))
        
        def api_callback(request, response, error):
            """Handle API responses/errors"""
            if error:
                print(f"API Error: {error}")
                asyncio.create_task(send_websocket_message(
                    websocket, "api_error", str(error)
                ))
            else:
                print(f"API Request: {request.method} {request.url}")
                if hasattr(response, 'status_code'):
                    print(f"API Response: {response.status_code}")
        
        print("Starting sampling loop...")
        await send_websocket_message(websocket, "debug", "Starting sampling loop...")
        
        updated_messages = await sampling_loop(
            model="claude-sonnet-4-20250514",
            provider=APIProvider.ANTHROPIC,
            system_prompt_suffix="",
            messages=anthropic_messages,
            output_callback=output_callback,
            tool_output_callback=tool_callback,
            api_response_callback=api_callback,
            api_key=settings.ANTHROPIC_API_KEY,
            tool_version="computer_use_20250124"
        )
        
        await send_websocket_message(websocket, "debug", f"Sampling loop completed with {len(updated_messages)} messages")
        
        for i, msg in enumerate(updated_messages):
            print(f"Message {i}: Role={msg.get('role')}, Type={type(msg)}")
            if hasattr(msg, 'content'):
                print(f"  Content type: {type(msg.content)}")
            elif 'content' in msg:
                print(f"  Content type: {type(msg['content'])}")
        
        new_messages = updated_messages[original_message_count:]
        
        if len(new_messages) == 0:
            print("WARNING: No new messages to save!")
            # This could happen if the sampling loop didn't generate any response
            await send_websocket_message(websocket, "debug", "No new messages generated")
        
        # Save new messages to database
        for i, msg in enumerate(new_messages):
            try:
                print(f"Processing new message {i+1}/{len(new_messages)}: {msg.get('role')}")
                
                # Convert content to JSON string for storage
                content_data = msg.get("content", [])
                content_str = json.dumps(content_data) if content_data else ""
                
                print(f"Saving message with role '{msg.get('role')}': {content_str[:100]}...")
                saved_msg = await session_manager.add_message(
                    session_id=session_id,
                    role=msg.get("role", "assistant"),
                    content=content_str
                )
                print(f"Successfully saved message: {saved_msg.id}")
                    
            except Exception as e:
                print(f"Error saving message {i}: {e}")
                import traceback
                traceback.print_exc()
                # Continue with other messages even if one fails
                continue
        
        # Verify messages were saved
        print("Verifying messages were saved...")
        final_messages = await session_manager.get_session_messages(session_id)
        print(f"Total messages in DB after processing: {len(final_messages)}")
        for msg in final_messages[-5:]:  # Show last 5 messages
            content_preview = msg.content[:50] if isinstance(msg.content, str) else str(msg.content)[:50]
            print(f"  - {msg.role}: {content_preview}...")
        
        # Send completion signal
        await send_websocket_message(websocket, "task_complete", "Task completed successfully")

    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        if session_id in active_connections:
            await send_websocket_message(active_connections[session_id], "error", error_msg)