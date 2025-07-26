import asyncio
import json

from anthropic.types.beta import BetaContentBlockParam
from app.services.connection_manager import RedisConnectionManager
from computer_use_demo.loop import sampling_loop, APIProvider

from app.config import settings
from app.services.session_manager import PostgresSessionManager
from app.utils.websocket import send_websocket_message


async def process_message_and_save(
        session_id: str,
        connection_manager: RedisConnectionManager,
        anthropic_messages: list,
        session_manager: PostgresSessionManager):
    """Process message with AI and save results to database"""
    try:
        if not await connection_manager.is_session_active(session_id):
            print(f"No websocket connection for session {session_id}")
            return

        websocket = await connection_manager.get_connection(session_id)
        if not websocket:
            print(f"No websocket connection for session {session_id}")
            return
        original_message_count = len(anthropic_messages)

        # Send debug info to client
        await send_websocket_message(websocket, "debug", f"Starting processing with {len(anthropic_messages)} messages")

        def output_callback(content: BetaContentBlockParam):
            """Handle assistant output"""
            print(f"Output callback received: {content}")
            if hasattr(content, 'model_dump'):
                content_dict = content.model_dump()  # type: ignore
            elif isinstance(content, dict):
                content_dict = content
            else:
                content_dict = {"type": "text", "text": str(content)}

            if not websocket:
                print(f"No websocket connection for session {session_id}")
                return
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

            if not websocket:
                print(f"No websocket connection for session {session_id}")
                return
            asyncio.create_task(send_websocket_message(
                websocket, "tool_result", result_dict
            ))

        def api_callback(request, response, error):
            """Handle API responses/errors"""
            if error:
                if not websocket:
                    print(f"No websocket connection for session {session_id}")
                    return
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

        print(
            f"AI processing complete. Generated {len(new_messages)} new messages. Now saving to database...")

        # Now save the results using the same session manager (same DB session
        # as the request)
        saved_count = 0
        for i, msg in enumerate(new_messages):
            try:
                print(
                    f"Processing new message {i+1}/{len(new_messages)}: {msg.get('role')}")

                # Convert content to JSON string for storage
                content_data = msg.get("content", [])
                content_str = json.dumps(content_data) if content_data else ""

                print(
                    f"Saving message with role '{msg.get('role')}': {content_str[:100]}...")
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

        print(
            f"Database save complete. Saved {saved_count}/{len(new_messages)} messages.")

        # Send completion signal
        await send_websocket_message(websocket, "task_complete", f"Task completed successfully. Saved {saved_count} new messages.")

    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        websocket = await connection_manager.get_connection(session_id)
        if websocket:
            await send_websocket_message(websocket, "error", error_msg)
