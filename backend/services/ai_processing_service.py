import asyncio
import logging
from dataclasses import dataclass

import orjson
from anthropic.types.beta import BetaContentBlockParam
from fastapi import WebSocket
from httpx import Request, Response

from backend.base.decorators import retry_on_exception, singleton
from backend.models.enums import Sender, TaskStatus
from backend.schemas import error as error_schemas, message as message_schemas
from backend.services.connection_manager import WebsocketsManager
from backend.services.session_manager import SessionManager
from backend.utils.convert import convert_to_anthropic_message
from backend.utils.websocket import send_websocket_message
from computer_use_demo.loop import sampling_loop
from computer_use_demo.tools.base import ToolResult

logger = logging.getLogger(__name__)


@singleton
@dataclass
class AIProcessingService:
    """Service for processing AI messages"""
    connection_manager: WebsocketsManager
    session_manager: SessionManager

    async def process_request(
        self,
        payload: message_schemas.SendMessageRequest,
    ):
        logger.info(
            f"Received message for session {payload.session_id}: {payload.message}")

        session = await self.session_manager.get_session(payload.session_id)
        if session is None:
            logger.warning(f"Session {payload.session_id} not found")
            return error_schemas.ErrorResponse(error="Session not found")

        # Check if session is connected
        if not await self.connection_manager.is_session_active(payload.session_id):
            logger.warning(f"Session {payload.session_id} not connected")
            return error_schemas.ErrorResponse(error="Session not connected")

        try:
            logger.info("Adding user message to database...")
            saved_message = await self.session_manager.add_user_message(
                session_id=payload.session_id,
                message=payload.message
            )
            logger.info(f"User message saved successfully: {saved_message.id}")

            db_messages = await self.session_manager.get_messages(payload.session_id)
            anthropic_messages = [
                convert_to_anthropic_message(msg) for msg in db_messages]

            logger.info("Starting background task to process message...")
            asyncio.create_task(
                self.process_message_and_save(
                    anthropic_messages=anthropic_messages,
                    payload=payload,
                ))

            return message_schemas.SendMessageResponse(status="processing")

        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            return error_schemas.ErrorResponse(
                error=f"Failed to process message: {str(e)}")

    async def _get_websocket_connection(self, session_id: str) -> WebSocket:
        """Get WebSocket connection for a session"""
        websocket = await self.connection_manager.get_connection(session_id)
        if not websocket:
            logger.warning(f"No websocket connection for session {session_id}")
            raise Exception(
                f"No websocket connection for session {session_id}")
        return websocket

    @retry_on_exception(max_retries=3, delay=1)
    async def send_messages_to_llm(
        self,
        websocket: WebSocket,
        messages: list,
        payload: message_schemas.SendMessageRequest,
    ):
        """
        Send API request to LLM

        Wrap sampling loop in a function to make it easier to test
        """
        return await sampling_loop(
            websocket=websocket,
            messages=messages,
            model=payload.model.value,
            provider=payload.api_provider,
            system_prompt_suffix=payload.system_prompt_suffix,
            output_callback=self.output_callback,
            tool_output_callback=self.tool_output_callback,
            api_response_callback=self.api_response_callback,
            api_key=payload.api_key,
            tool_version=payload.tool_version.value,
            max_tokens=payload.max_tokens,
            thinking_budget=payload.thinking_budget,
        )

    async def process_message_and_save(
        self,
        anthropic_messages: list,
        payload: message_schemas.SendMessageRequest,
    ):
        """Process message with AI and save results to database"""
        try:
            websocket = await self._get_websocket_connection(payload.session_id)
            original_message_count = len(anthropic_messages)

            # Send debug info to client
            await send_websocket_message(
                websocket,
                TaskStatus.PENDING,
                "debug",
                f"Starting processing with {len(anthropic_messages)} messages"
            )

            await send_websocket_message(
                websocket,
                TaskStatus.RUNNING,
                "debug",
                "Starting sampling loop...",
            )

            updated_messages = []

            logger.info("Starting sampling loop with following parameters:"
                        f"model={payload.model}, provider={payload.api_provider},"
                        f"system_prompt_suffix={payload.system_prompt_suffix},"
                        f"tool_version={payload.tool_version}, max_tokens={payload.max_tokens},"
                        f"thinking_budget={payload.thinking_budget}")

            updated_messages = await self.send_messages_to_llm(
                websocket,
                messages=anthropic_messages,
                payload=payload
            )

            await send_websocket_message(
                websocket,
                TaskStatus.RUNNING,
                "debug",
                f"Sampling loop completed with {len(updated_messages)} messages",
            )

            # Extract only the new messages that were generated
            new_messages = updated_messages[original_message_count:]

            if len(new_messages) == 0:
                logger.info(f"Previous messages: {updated_messages}")
                logger.warning("No new messages to save!")
                await send_websocket_message(
                    websocket,
                    TaskStatus.COMPLETED,
                    "task_complete",
                    "Task completed - no new messages",
                )
                return

            logger.info(f"AI processing complete. Generated {len(new_messages)}"
                        " new messages. Now saving to database...")

            # Save the results using batch operation for better performance
            try:
                logger.info(f"Saving {len(new_messages)} messages in batch...")

                # Save all messages in a single transaction
                saved_messages = await self.session_manager.add_messages_batch(
                    session_id=payload.session_id,
                    raw_messages=new_messages
                )

                logger.info(
                    f"Successfully saved {len(saved_messages)} messages in batch")
                saved_count = len(saved_messages)

            except Exception as e:
                logger.error(f"Error saving messages batch: {e}")
                # Fallback to individual saves if batch fails
                logger.info("Falling back to individual message saves...")
                saved_count = 0
                for i, msg in enumerate(new_messages):
                    try:
                        content_data = msg.get("content", {})
                        content_json = orjson.dumps(
                            content_data).decode("utf-8")

                        await self.session_manager.add_message(
                            session_id=payload.session_id,
                            role=Sender.BOT if msg.get(
                                "role") == "assistant" else Sender.TOOL,
                            content=content_json
                        )
                        saved_count += 1
                    except Exception as fallback_error:
                        logger.error(
                            f"Error saving individual message {i}: {fallback_error}")
                        continue

                logger.info(
                    f"Fallback save complete. Saved {saved_count}/{len(new_messages)} messages.")

            # Send completion signal
            await send_websocket_message(
                websocket,
                TaskStatus.COMPLETED,
                "task_complete",
                f"Task completed successfully. Saved {saved_count} new messages.",
            )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            restored_websocket = await self.connection_manager.get_connection(payload.session_id)
            if restored_websocket:
                await send_websocket_message(
                    restored_websocket,
                    TaskStatus.ERROR,
                    "error",
                    "Failed to process message",
                )

    @staticmethod
    def output_callback(websocket: WebSocket, content: BetaContentBlockParam):
        """Handle assistant output"""
        logger.info(f"Output callback received: {content.get('text')}")
        if hasattr(content, 'model_dump'):
            content_dict = content.model_dump()  # type: ignore
        elif isinstance(content, dict):
            content_dict = content
        else:
            content_dict = {"type": "text", "text": str(content)}

        asyncio.create_task(send_websocket_message(
            websocket,
            TaskStatus.RUNNING,
            "assistant_message",
            content_dict
        ))

    @staticmethod
    def tool_output_callback(websocket: WebSocket, result: ToolResult, tool_id: str):
        """Handle tool results"""
        logger.info(f"Tool callback - ID: {tool_id}")
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
            websocket,
            TaskStatus.RUNNING,
            "tool_result",
            result_dict
        ))

    @staticmethod
    def api_response_callback(
            websocket: WebSocket,
            request: Request,
            response: Response | object | None,
            error: Exception | None):
        """Handle API responses/errors"""
        if error:
            asyncio.create_task(send_websocket_message(
                websocket,
                TaskStatus.ERROR,
                "error",
                f"API Error: {str(error)}"
            ))
        else:
            logger.info(f"API Request: {request.method} {request.url}")
            if hasattr(response, 'status_code'):
                logger.info(f"API Response: {response.status_code}") # type: ignore
