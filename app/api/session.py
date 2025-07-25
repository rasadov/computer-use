from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict
import json
import asyncio
from app.models.message import ChatMessage
from computer_use_demo.loop import sampling_loop, APIProvider
from app.dependencies import get_session_manager
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
        
        # Get all existing messages for processing
        db_messages = await session_manager.get_session_messages(session_id)
        anthropic_messages = [convert_to_anthropic_message(msg) for msg in db_messages]
        
        # Start agent processing and handle results
        print(f"Starting background task to process message...")
        asyncio.create_task(process_message_and_save(session_id, anthropic_messages, session_manager))
        
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

async def process_message_and_save(session_id: str, anthropic_messages: list, session_manager: PostgresSessionManager):
    """Process message with AI and save results to database"""
    try:
        if session_id not in active_connections:
            print(f"No websocket connection for session {session_id}")
            return
            
        websocket = active_connections[session_id]
        original_message_count = len(anthropic_messages)
        
        # Send debug info to client
        await send_websocket_message(websocket, "debug", f"Starting processing with {len(anthropic_messages)} messages")
    
        def output_callback(content: BetaContentBlockParam):
            """Handle assistant output"""
            print(f"Output callback received: {content}")
            if hasattr(content, 'model_dump'):
                content_dict = content.model_dump() # type: ignore
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
                    websocket, "error", f"API Error: {str(error)}"
                ))
            else:
                print(f"API Request: {request.method} {request.url}")
                if hasattr(response, 'status_code'):
                    print(f"API Response: {response.status_code}")
        
        print("Starting sampling loop...")
        await send_websocket_message(websocket, "debug", "Starting sampling loop...")
        
        try:
            # This is the pure AI processing - no database operations
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
        except Exception as e:
            error_msg = f"Sampling loop failed: {str(e)}"
            print(error_msg)
            await send_websocket_message(websocket, "error", error_msg)
            return
        
        await send_websocket_message(websocket, "debug", f"Sampling loop completed with {len(updated_messages)} messages")
        
        # Extract only the new messages that were generated
        new_messages = updated_messages[original_message_count:]
        
        if len(new_messages) == 0:
            print("WARNING: No new messages to save!")
            await send_websocket_message(websocket, "debug", "No new messages generated")
            await send_websocket_message(websocket, "task_complete", "Task completed - no new messages")
            return
        
        print(f"AI processing complete. Generated {len(new_messages)} new messages. Now saving to database...")
        
        # Now save the results using the same session manager (same DB session as the request)
        saved_count = 0
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
                saved_count += 1
                    
            except Exception as e:
                print(f"Error saving message {i}: {e}")
                import traceback
                traceback.print_exc()
                # Continue with other messages even if one fails
                continue
        
        print(f"Database save complete. Saved {saved_count}/{len(new_messages)} messages.")
        
        # Send completion signal
        await send_websocket_message(websocket, "task_complete", f"Task completed successfully. Saved {saved_count} new messages.")

    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        if session_id in active_connections:
            await send_websocket_message(active_connections[session_id], "error", error_msg)