import asyncio
import logging

from anthropic.types.beta import BetaContentBlockParam
from fastapi import WebSocket
from httpx import Request, Response
import orjson

from backend.base.decorators import singleton
from backend.models.enums import LLMModel, Sender, ToolVersion
from backend.services.connection_manager import WebsocketsManager
from backend.services.session_manager import SessionManager
from backend.models.enums import TaskStatus
from backend.utils.websocket import send_websocket_message
from computer_use_demo.loop import sampling_loop, APIProvider
from computer_use_demo.tools.base import ToolResult


logger = logging.getLogger(__name__)


@singleton
class AIProcessingService:
    """Service for processing AI messages"""
    def __init__(
            self,
            connection_manager: WebsocketsManager,
            session_manager: SessionManager):
        self.connection_manager = connection_manager
        self.session_manager = session_manager

    async def _get_websocket_connection(self, session_id: str) -> WebSocket:
        """Get WebSocket connection for a session"""
        websocket = await self.connection_manager.get_connection(session_id)
        if not websocket:
            logger.warning(f"No websocket connection for session {session_id}")
            raise Exception(f"No websocket connection for session {session_id}")
        return websocket

    async def send_messages_to_llm(
        self,
        messages: list,
        model: LLMModel,
        api_provider: APIProvider,
        system_prompt_suffix: str,
        output_callback,
        tool_output_callback,
        api_response_callback,
        api_key: str,
        tool_version: ToolVersion,
        max_tokens: int,
        thinking_budget: int | None,
    ):
        """
        Send API request to LLM

        Wrap sampling loop in a function to make it easier to test
        """
        return await sampling_loop(
            messages=messages,
            model=model.value,
            provider=api_provider,
            system_prompt_suffix=system_prompt_suffix,
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            api_response_callback=api_response_callback,
            api_key=api_key,
            tool_version=tool_version.value,
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
        )

    async def process_message_and_save(
        self,
        session_id: str,
        anthropic_messages: list,
        *,
        model: LLMModel,
        api_provider: APIProvider,
        api_key: str,
        system_prompt_suffix: str,
        tool_version: ToolVersion,
        max_tokens: int,
        thinking_budget: int | None,
        max_retries: int,
    ):
        """Process message with AI and save results to database"""
        try:
            websocket = await self._get_websocket_connection(session_id)
            original_message_count = len(anthropic_messages)

            # Send debug info to client
            await send_websocket_message(
                websocket,
                TaskStatus.PENDING,
                "debug",
                f"Starting processing with {len(anthropic_messages)} messages"
            )

            # Callbacks for AI processing

            def output_callback(content: BetaContentBlockParam):
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

            def tool_output_callback(result: ToolResult, tool_id: str):
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

            def api_response_callback(
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

            await send_websocket_message(
                websocket,
                TaskStatus.RUNNING,
                "debug",
                "Starting sampling loop...",
            )

            updated_messages = []

            logger.info("Starting sampling loop with following parameters:"
                        f"model={model}, provider={api_provider},"
                        f"system_prompt_suffix={system_prompt_suffix},"
                        f"tool_version={tool_version}, max_tokens={max_tokens},"
                        f"thinking_budget={thinking_budget}")

            # Try up to max_retries times
            for i in range(max_retries):
                try:
                    # This is the pure AI processing - no database operations
                    updated_messages = await self.send_messages_to_llm(
                        messages=anthropic_messages,
                        model=model,
                        api_provider=api_provider,
                        system_prompt_suffix=system_prompt_suffix,
                        output_callback=output_callback,
                        tool_output_callback=tool_output_callback,
                        api_response_callback=api_response_callback,
                        api_key=api_key,
                        tool_version=tool_version,
                        max_tokens=max_tokens,
                        thinking_budget=thinking_budget,
                    )
                    break
                except Exception as e:
                    logger.error(f"Try {i+1} - Sampling loop failed: {str(e)}")
            else:
                # If we get here, it means we've tried max_retries times and failed
                logger.error("Sampling loop failed after multiple retries")
                await send_websocket_message(
                    websocket,
                    TaskStatus.ERROR,
                    "error",
                    "Failed to process message"
                )
                return

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
                    session_id=session_id,
                    raw_messages=new_messages
                )
                
                logger.info(f"Successfully saved {len(saved_messages)} messages in batch")
                saved_count = len(saved_messages)
                
            except Exception as e:
                logger.error(f"Error saving messages batch: {e}")
                # Fallback to individual saves if batch fails
                logger.info("Falling back to individual message saves...")
                saved_count = 0
                for i, msg in enumerate(new_messages):
                    try:
                        content_data = msg.get("content", {})
                        content_json = orjson.dumps(content_data).decode("utf-8")
                        
                        await self.session_manager.add_message(
                            session_id=session_id,
                            role=Sender.BOT if msg.get("role") == "assistant" else Sender.TOOL,
                            content=content_json
                        )
                        saved_count += 1
                    except Exception as fallback_error:
                        logger.error(f"Error saving individual message {i}: {fallback_error}")
                        continue
                
                logger.info(f"Fallback save complete. Saved {saved_count}/{len(new_messages)} messages.")

            # Send completion signal
            await send_websocket_message(
                websocket,
                TaskStatus.COMPLETED,
                "task_complete",
                f"Task completed successfully. Saved {saved_count} new messages.",
            )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            websocket = await self.connection_manager.get_connection(session_id)
            if websocket:
                await send_websocket_message(
                    websocket,
                    TaskStatus.ERROR,
                    "error",
                    "Failed to process message",
                )
