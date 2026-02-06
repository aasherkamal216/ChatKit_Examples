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
    ThreadMetadata,
    UserMessageItem,
    ThreadStreamEvent,
    AssistantMessageItem,
    AssistantMessageContent,
    ThreadItemDoneEvent,
    AudioInput,
    TranscriptionResult,
    Action,
    WidgetItem,
    UserMessageTagContent,
    ImageAttachment,
    UserMessageTextContent,
    ProgressUpdateEvent,
    ClientEffectEvent,
    Workflow,
    CustomTask,
)
from chatkit.agents import (
    AgentContext,
    stream_agent_response,
    ThreadItemConverter,
    ResponseStreamConverter,
)
from agents import Runner

from .types import RequestContext
from .agent import my_agent

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
UPLOAD_DIR = Path("uploads")


class LocalConverter(ThreadItemConverter):
    async def tag_to_message_content(
        self, tag: UserMessageTagContent
    ) -> ResponseInputTextParam:
        return ResponseInputTextParam(
            type="input_text", text=f"\n[User tagged: {tag.text}]\n"
        )

    async def attachment_to_message_content(self, attachment):
        file_path = next(
            (f for f in UPLOAD_DIR.iterdir() if f.stem == attachment.id), None
        )
        if not file_path:
            return ResponseInputTextParam(type="input_text", text="[File not found]")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        if isinstance(attachment, ImageAttachment) or attachment.mime_type.startswith(
            "image/"
        ):
            b64 = base64.b64encode(file_bytes).decode("utf-8")
            return ResponseInputImageParam(
                type="input_image",
                detail="auto",
                image_url=f"data:{attachment.mime_type};base64,{b64}",
            )
        try:
            return ResponseInputTextParam(
                type="input_text",
                text=f"\n[File {attachment.name}]:\n{file_bytes.decode('utf-8')}\n",
            )
        except:
            return ResponseInputTextParam(
                type="input_text", text=f"[Binary file {attachment.name}]"
            )


class LocalResponseConverter(ResponseStreamConverter):
    async def base64_image_to_url(
        self, image_id: str, base64_image: str, partial_image_index: int | None = None
    ) -> str:
        return f"data:image/png;base64,{base64_image}"


class MyChatKitServer(ChatKitServer[RequestContext]):

    async def respond(
        self,
        thread: ThreadMetadata,
        input_message: UserMessageItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:

        items_page = await self.store.load_thread_items(
            thread.id, None, 20, "desc", context
        )
        items = list(reversed(items_page.data))

        if len(items) <= 1 and input_message:
            asyncio.create_task(self._generate_thread_title(thread, items, context))

        agent_context = AgentContext(
            thread=thread, store=self.store, request_context=context
        )

        # --- Visual Workflow for Search ---
        # If the user input looks like a search, we show a workflow item
        user_text = "".join(
            [p.text for p in input_message.content if hasattr(p, "text")]
        )
        if "search" in user_text.lower() or "find" in user_text.lower():
            await agent_context.start_workflow(
                Workflow(
                    type="custom",
                    tasks=[
                        CustomTask(
                            title="Initializing search...", status_indicator="loading"
                        )
                    ],
                )
            )

        converter = LocalConverter()
        agent_inputs = await converter.to_agent_input(items)

        if input_message and input_message.inference_options:
            selected_model = input_message.inference_options.model
            if selected_model:

                my_agent.model = selected_model
        result = Runner.run_streamed(my_agent, agent_inputs, context=agent_context)

        async for event in stream_agent_response(
            agent_context, result, converter=LocalResponseConverter(partial_images=3)
        ):
            # If the agent starts a tool, update the workflow
            if (
                event.type == "thread.item.added"
                and event.item.type == "assistant_message"
            ):
                await agent_context.end_workflow()

            yield event

    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:

        # --- Handle Theme Application Effect ---
        if action.type == "apply_theme_effect":
            # 1. Send a "Thinking" progress update
            yield ProgressUpdateEvent(text="Applying new styles...", icon="sparkle")
            await asyncio.sleep(1)  # Fake delay for effect

            # 2. Emit the Client Effect!
            # This 'name' will be listened for in index.html
            yield ClientEffectEvent(
                name="update_ui_theme",
                data=action.payload,  # The theme object from preview_theme tool
            )

            # 3. Confirm in chat
            yield ThreadItemDoneEvent(
                item=AssistantMessageItem(
                    id=self.store.generate_item_id("message", thread, context),
                    thread_id=thread.id,
                    created_at=datetime.now(),
                    content=[
                        AssistantMessageContent(text="Theme applied successfully!")
                    ],
                )
            )

        elif action.type == "submit_feedback":
            yield ThreadItemDoneEvent(
                item=AssistantMessageItem(
                    id=self.store.generate_item_id("message", thread, context),
                    thread_id=thread.id,
                    created_at=datetime.now(),
                    content=[
                        AssistantMessageContent(text="Feedback received. Thank you!")
                    ],
                )
            )

    async def _generate_thread_title(
        self, thread: ThreadMetadata, items: List[Any], context: RequestContext
    ):
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
                model="gpt-5-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize this message into a 3-word title. Return only the title text.",
                    },
                    {"role": "user", "content": first_text},
                ],
            )
            new_title = res.choices[0].message.content.strip().replace('"', "")

            # Update Store
            thread.title = new_title
            await self.store.save_thread(thread, context)
            # Note: ChatKit handles updating the UI title automatically
            # if the store is updated during the request flow.
        except Exception as e:
            print(f"Titling error: {e}")

    async def transcribe(
        self, audio_input: AudioInput, context: RequestContext
    ) -> TranscriptionResult:
        f = io.BytesIO(audio_input.data)
        f.name = "voice.webm"
        transcription = await client.audio.transcriptions.create(
            model="whisper-1", file=f
        )
        return TranscriptionResult(text=transcription.text)
