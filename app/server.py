import io
import base64
import asyncio
from pathlib import Path
from typing import AsyncIterator, Any, List
from datetime import datetime
from openai import AsyncOpenAI
from openai.types.responses import ResponseInputTextParam, ResponseInputImageParam
import os

from chatkit.server import ChatKitServer, stream_widget
from chatkit.types import (
    ThreadMetadata, UserMessageItem, ThreadStreamEvent, 
    AssistantMessageItem, AssistantMessageContent, ThreadItemDoneEvent,
    AudioInput, TranscriptionResult, Action, WidgetItem, UserMessageTagContent,
    ImageAttachment, FileAttachment, ThreadUpdatedEvent, UserMessageTextContent
)
from chatkit.agents import (
    AgentContext, stream_agent_response,
    ThreadItemConverter, ResponseStreamConverter
)
from agents import Runner

from .types import RequestContext
from .agent import my_agent

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
UPLOAD_DIR = Path("uploads")

class LocalConverter(ThreadItemConverter):
    async def tag_to_message_content(self, tag: UserMessageTagContent) -> ResponseInputTextParam:
        return ResponseInputTextParam(type="input_text", text=f"\n[User tagged: {tag.text}]\n")

    async def attachment_to_message_content(self, attachment):
        file_path = next((f for f in UPLOAD_DIR.iterdir() if f.stem == attachment.id), None)
        if not file_path: return ResponseInputTextParam(type="input_text", text="[File not found]")
        
        with open(file_path, "rb") as f: file_bytes = f.read()

        if isinstance(attachment, ImageAttachment) or attachment.mime_type.startswith("image/"):
            b64 = base64.b64encode(file_bytes).decode("utf-8")
            return ResponseInputImageParam(type="input_image", detail="auto", 
                                         image_url=f"data:{attachment.mime_type};base64,{b64}")
        try:
            return ResponseInputTextParam(type="input_text", text=f"\n[File {attachment.name}]:\n{file_bytes.decode('utf-8')}\n")
        except:
            return ResponseInputTextParam(type="input_text", text=f"[Binary file {attachment.name}]")

class LocalResponseConverter(ResponseStreamConverter):
    async def base64_image_to_url(self, image_id: str, b64: str, index: int | None = None) -> str:
        return f"data:image/png;base64,{b64}"

class MyChatKitServer(ChatKitServer[RequestContext]):
    
    async def respond(self, thread: ThreadMetadata, input_message: UserMessageItem | None, 
                      context: RequestContext) -> AsyncIterator[ThreadStreamEvent]:
        
        # 1. Load History
        items_page = await self.store.load_thread_items(thread.id, None, 20, "desc", context)
        items = list(reversed(items_page.data))
        
        # 2. Auto-Title logic
        # If this is the first user message, generate a title
        if len(items) <= 1 and input_message:
            asyncio.create_task(self._generate_thread_title(thread, items, context))

        # 3. Process with Agent
        converter = LocalConverter()
        agent_inputs = await converter.to_agent_input(items)
        active_agent = my_agent
        if input_message and input_message.inference_options:
            selected_model = input_message.inference_options.model
            if selected_model:
                # Agent is a Pydantic model, so we can use model_copy with update
                active_agent = my_agent
                active_agent.model = selected_model

        agent_context = AgentContext(thread=thread, store=self.store, request_context=context)
        result = Runner.run_streamed(active_agent, agent_inputs, context=agent_context)
        
        async for event in stream_agent_response(agent_context, result, 
                                               converter=LocalResponseConverter(partial_images=3)):
            yield event

    async def _generate_thread_title(self, thread: ThreadMetadata, items: List[Any], context: RequestContext):
        """Background task to summarize the conversation into a title."""
        try:
            # Find the first user text
            first_text = "New Conversation"
            for item in items:
                if isinstance(item, UserMessageItem):
                    for part in item.content:
                        if isinstance(part, UserMessageTextContent):
                            first_text = part.text
                            break
                    break
            
            # Call GPT for a quick summary
            res = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Summarize this message into a 3-word title. Return only the title text."},
                          {"role": "user", "content": first_text}]
            )
            new_title = res.choices[0].message.content.strip().replace('"', '')
            
            # Update Store
            thread.title = new_title
            await self.store.save_thread(thread, context)
            # Note: ChatKit handles updating the UI title automatically 
            # if the store is updated during the request flow.
        except Exception as e:
            print(f"Titling error: {e}")

    async def transcribe(self, audio_input: AudioInput, context: RequestContext) -> TranscriptionResult:
        f = io.BytesIO(audio_input.data)
        f.name = "voice.webm"
        transcription = await client.audio.transcriptions.create(model="whisper-1", file=f)
        return TranscriptionResult(text=transcription.text)

    async def action(self, thread: ThreadMetadata, action: Action[str, Any], 
                     sender: WidgetItem | None, context: RequestContext) -> AsyncIterator[ThreadStreamEvent]:
        if action.type == "submit_feedback":
            yield ThreadItemDoneEvent(item=AssistantMessageItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id, created_at=datetime.now(),
                content=[AssistantMessageContent(text="Feedback received. Thank you!")]
            ))