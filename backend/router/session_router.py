import asyncio
import logging

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends
)

from backend.core.dependencies import (
    get_session_manager,
    get_connection_manager,
    get_ai_processing_service,
    get_session_manager_websocket,
    get_connection_manager_websocket
)
from backend.models.enums import SessionStatus, Sender
from backend.services.ai_processing_service import AIProcessingService
from backend.services.connection_manager import RedisConnectionManager
from backend.services.session_manager import SessionManager
from backend.utils.convert import convert_to_anthropic_message
from backend.schemas import session as session_schemas
from backend.schemas import message as message_schemas
from backend.schemas import error as error_schemas


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions",
             response_model=session_schemas.CreateSessionResponse,
             tags=["Sessions"]
             )
async def create_session(
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Create a new session"""
    session_id = await session_manager.create_session()
    return session_schemas.CreateSessionResponse(session_id=session_id)


@router.get("/sessions",
            response_model=session_schemas.ListSessionsResponse,
            tags=["Sessions"]
            )
async def list_sessions(
    session_manager: SessionManager = Depends(get_session_manager),
):
    """List all sessions"""
    sessions = await session_manager.list_sessions()

    return session_schemas.ListSessionsResponse(
        sessions=[
            session_schemas.SessionInfo(
                id=s.id,
                status=s.status,
                created_at=s.created_at
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
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Get a session by id"""
    session = await session_manager.get_session(session_id)
    if session is None:
        return error_schemas.ErrorResponse(error="Session not found")

    messages = await session_manager.get_session_messages(session_id)

    return session_schemas.GetSessionResponse(
        id=session.id,
        status=session.status,
        created_at=session.created_at,
        messages=[
            session_schemas.MessageInfo(
                role=m.role,
                content=m.content
            )
            for m in messages
        ]
    )


@router.post("/sessions/{session_id}/messages",
             response_model=message_schemas.SendMessageResponse,
             tags=["Sessions"]
             )
async def send_message(
    payload: message_schemas.SendMessageRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    connection_manager: RedisConnectionManager = Depends(get_connection_manager),
    ai_processing_service: AIProcessingService = Depends(get_ai_processing_service),
):
    """Send a message to a session"""
    logger.info(f"Received message for session {payload.session_id}: {payload.message}")

    session = await session_manager.get_session(payload.session_id)
    if session is None:
        logger.warning(f"Session {payload.session_id} not found")
        return error_schemas.ErrorResponse(error="Session not found")

    # Check if session is connected
    if not await connection_manager.is_session_active(payload.session_id):
        logger.warning(f"Session {payload.session_id} not connected")
        return error_schemas.ErrorResponse(error="Session not connected")

    try:
        logger.debug(f"Adding user message to database...")
        saved_message = await session_manager.add_user_message(
            session_id=payload.session_id,
            message=payload.message
        )
        logger.debug(f"User message saved successfully: {saved_message.id}")

        db_messages = await session_manager.get_session_messages(payload.session_id)
        anthropic_messages = [
            convert_to_anthropic_message(msg) for msg in db_messages]

        logger.debug(f"Starting background task to process message...")
        logger.info(f"anthropic messages: {anthropic_messages}")
        asyncio.create_task(
            ai_processing_service.process_message_and_save(
                payload.session_id,
                anthropic_messages,
            ))

        return message_schemas.SendMessageResponse(status="processing")

    except Exception as e:
        logger.error(f"Failed to process message: {str(e)}")
        return error_schemas.ErrorResponse(
            error=f"Failed to process message: {str(e)}")


@router.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager_websocket),
    connection_manager: RedisConnectionManager = Depends(get_connection_manager_websocket),
):
    """WebSocket endpoint for real-time updates from the agent"""
    await websocket.accept()
    logger.debug(f"Accepted WebSocket connection for session {session_id}")
    await session_manager.update_session_status(session_id, SessionStatus.ACTIVE)
    await connection_manager.add_connection(session_id, websocket)

    async def cleanup():
        """Cleanup function to remove connection and update session status"""
        logger.debug(f"Cleaning up session {session_id}")
        try:
            await connection_manager.remove_connection(session_id)
            await session_manager.update_session_status(session_id, SessionStatus.INACTIVE)
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")

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
        await cleanup()
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await cleanup()
