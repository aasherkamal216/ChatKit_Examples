import io
import base64
from pathlib import Path
from typing import AsyncIterator, Any
from datetime import datetime
from openai import AsyncOpenAI
from openai.types.responses import ResponseInputTextParam, ResponseInputImageParam
import os

from chatkit.server import ChatKitServer, stream_widget
from chatkit.types import (
    ThreadMetadata, UserMessageItem, ThreadStreamEvent, 
    AssistantMessageItem, AssistantMessageContent, ThreadItemDoneEvent,
    AudioInput, TranscriptionResult, Action, WidgetItem, UserMessageTagContent,
    ImageAttachment, FileAttachment
)
from chatkit.agents import (
    AgentContext, stream_agent_response,
    ThreadItemConverter, ResponseStreamConverter
)
from chatkit.widgets import Card, Text
from agents import Runner

from .types import RequestContext
from .agent import my_agent

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
UPLOAD_DIR = Path("uploads")

# FIX 1: Enhanced Converter for Attachments & Tags
class LocalConverter(ThreadItemConverter):
    
    async def tag_to_message_content(self, tag: UserMessageTagContent) -> ResponseInputTextParam:
        return ResponseInputTextParam(
            type="input_text",
            text=f"\n[User tagged entity: {tag.text} (ID: {tag.id})]\n"
        )

    async def attachment_to_message_content(self, attachment):
        """
        Reads local files and converts them for the LLM.
        For localhost, we must use Base64 for images because OpenAI cannot access http://localhost:8000.
        """
        # Reconstruct filename from ID + extension logic in main.py
        # We search for the file because we stored it as {id}{ext}
        file_path = None
        for f in UPLOAD_DIR.iterdir():
            if f.stem == attachment.id:
                file_path = f
                break
        
        if not file_path or not file_path.exists():
            return ResponseInputTextParam(type="input_text", text=f"[Attachment {attachment.name} not found]")

        # Read file bytes
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # Handle Images
        if isinstance(attachment, ImageAttachment) or attachment.mime_type.startswith("image/"):
            b64_data = base64.b64encode(file_bytes).decode("utf-8")
            return ResponseInputImageParam(
                type="input_image",
                detail="auto",
                image_url=f"data:{attachment.mime_type};base64,{b64_data}"
            )
        
        # Handle Text Files (Simple read)
        # For PDFs/Docs in production, you would use OpenAI File Search tool or a parsing library.
        try:
            text_content = file_bytes.decode("utf-8")
            return ResponseInputTextParam(
                type="input_text", 
                text=f"\n[Content of file {attachment.name}]:\n{text_content}\n"
            )
        except UnicodeDecodeError:
            return ResponseInputTextParam(
                type="input_text", 
                text=f"[Binary file {attachment.name} attached but cannot be read as text]"
            )

class LocalResponseConverter(ResponseStreamConverter):
    async def base64_image_to_url(self, image_id: str, base64_image: str, partial_image_index: int | None = None) -> str:
        return f"data:image/png;base64,{base64_image}"

class MyChatKitServer(ChatKitServer[RequestContext]):
    
    async def respond(
        self, 
        thread: ThreadMetadata, 
        input_message: UserMessageItem | None, 
        context: RequestContext
    ) -> AsyncIterator[ThreadStreamEvent]:
        
        # 1. Load history
        items_page = await self.store.load_thread_items(
            thread.id, None, 20, "desc", context
        )
        items = list(reversed(items_page.data))
        
        # 2. Convert to Agent inputs
        converter = LocalConverter()
        agent_inputs = await converter.to_agent_input(items)
        
        # FIX 2: Handle Dynamic Model Selection
        # We clone the default agent and override the model if the user selected one.
        active_agent = my_agent
        if input_message and input_message.inference_options:
            selected_model = input_message.inference_options.model
            if selected_model:
                # Agent is a Pydantic model, so we can use model_copy with update
                active_agent = my_agent
                active_agent.model = selected_model

        # 3. Run Agent
        agent_context = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context
        )
        
        result = Runner.run_streamed(active_agent, agent_inputs, context=agent_context)
        
        # 4. Stream response
        async for event in stream_agent_response(
            agent_context, 
            result, 
            converter=LocalResponseConverter(partial_images=3)
        ):
            yield event

    async def transcribe(self, audio_input: AudioInput, context: RequestContext) -> TranscriptionResult:
        ext = {
            "audio/webm": "webm",
            "audio/mp4": "m4a", 
            "audio/ogg": "ogg",
            "audio/wav": "wav"
        }.get(audio_input.media_type, "webm")

        f = io.BytesIO(audio_input.data)
        f.name = f"voice.{ext}"

        transcription = await client.audio.transcriptions.create(
            model="whisper-1", 
            file=f
        )
        return TranscriptionResult(text=transcription.text)

    async def action(
        self, 
        thread: ThreadMetadata, 
        action: Action[str, Any], 
        sender: WidgetItem | None, 
        context: RequestContext
    ) -> AsyncIterator[ThreadStreamEvent]:
        
        if action.type == "submit_feedback":
            user_comment = action.payload.get("user_comment", "")
            print(f"Feedback received from {context.user_id}: {user_comment}")
            
            yield ThreadItemDoneEvent(
                item=AssistantMessageItem(
                    id=self.store.generate_item_id("message", thread, context),
                    thread_id=thread.id,
                    created_at=datetime.now(),
                    content=[AssistantMessageContent(text="Feedback received. Thank you!")]
                )
            )