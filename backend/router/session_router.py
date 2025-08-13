import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from backend.dependencies import get_session_manager
from backend.services.ai_processing_service import process_message_and_save
from backend.services.session_manager import SessionManager
from backend.utils.convert import convert_to_anthropic_message
from backend.services.connection_manager import connection_manager
from backend.schemas import session as session_schemas

router = APIRouter()


@router.post("/sessions",
             response_model=session_schemas.CreateSessionResponse,
             tags=["Sessions"]
             )
async def create_session(
        session_manager: SessionManager = Depends(get_session_manager)):
    session_id = await session_manager.create_session()
    return session_schemas.CreateSessionResponse(session_id=session_id)


@router.get("/sessions",
            response_model=session_schemas.ListSessionsResponse,
            tags=["Sessions"]
            )
async def list_sessions(
        session_manager: SessionManager = Depends(get_session_manager)):
    sessions = await session_manager.list_sessions()

    # Also get active sessions from Redis
    active_redis_sessions = await connection_manager.get_active_sessions()

    return session_schemas.ListSessionsResponse(
        sessions=[
            session_schemas.SessionInfo(
                id=s.id,
                status=s.status,
                created_at=s.created_at,
                is_connected=s.id in active_redis_sessions
            )
            for s in sessions
        ]
    )


@router.get("/sessions/{session_id}",
            response_model=session_schemas.GetSessionResponse,
            tags=["Sessions"]
            )
async def get_session(
        session_id: str,
        session_manager: SessionManager = Depends(get_session_manager)):
    session = await session_manager.get_session(session_id)
    if session is None:
        return session_schemas.ErrorResponse(error="Session not found")

    messages = await session_manager.get_session_messages(session_id)
    is_connected = await connection_manager.is_session_active(session_id)

    return session_schemas.GetSessionResponse(
        id=session.id,
        status=session.status,
        created_at=session.created_at,
        is_connected=is_connected,
        messages=[
            session_schemas.MessageInfo(
                role=m.role,
                content=m.content
            )
            for m in messages
        ]
    )


@router.post("/sessions/{session_id}/messages",
             response_model=session_schemas.SendMessageResponse,
             tags=["Sessions"]
             )
async def send_message(
        session_id: str,
        message: dict,
        session_manager: SessionManager = Depends(get_session_manager)):
    print(f"Received message for session {session_id}: {message}")

    session = await session_manager.get_session(session_id)
    if session is None:
        print(f"Session {session_id} not found")
        return session_schemas.ErrorResponse(error="Session not found")

    # Check if session is connected
    if not await connection_manager.is_session_active(session_id):
        return session_schemas.ErrorResponse(error="Session not connected")

    try:
        print(f"Adding user message to database...")
        saved_message = await session_manager.add_message(
            session_id=session_id,
            role="user",
            content=message["content"]
        )
        print(f"User message saved successfully: {saved_message.id}")

        db_messages = await session_manager.get_session_messages(session_id)
        anthropic_messages = [
            convert_to_anthropic_message(msg) for msg in db_messages]

        print(f"Starting background task to process message...")
        asyncio.create_task(
            process_message_and_save(
                session_id,
                connection_manager,
                anthropic_messages,
                session_manager))

        return session_schemas.SendMessageResponse(status="processing")

    except Exception as e:
        print(f"Error in send_message: {e}")
        import traceback
        traceback.print_exc()
        return session_schemas.ErrorResponse(
            error=f"Failed to process message: {str(e)}")


@router.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates from the agent"""
    await websocket.accept()
    await connection_manager.add_connection(session_id, websocket)

    try:
        # Send connection confirmation
        await connection_manager.send_to_session(
            session_id,
            "connection_established",
            f"Connected to session {session_id}"
        )

        while True:
            # Keep connection alive
            await websocket.receive_text()

    except WebSocketDisconnect:
        await connection_manager.remove_connection(session_id)
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        await connection_manager.remove_connection(session_id)


@router.get("/sessions/health/redis",
            response_model=session_schemas.RedisHealthResponse,
            tags=["Sessions"]
            )
async def redis_health():
    try:
        active_sessions = await connection_manager.get_active_sessions()
        return session_schemas.RedisHealthResponse(
            status="healthy",
            active_sessions=len(active_sessions),
            sessions=list(active_sessions.keys()),
            error=None
        )
    except Exception as e:
        return session_schemas.RedisHealthResponse(
            status="unhealthy",
            active_sessions=None,
            sessions=None,
            error=str(e)
        )
