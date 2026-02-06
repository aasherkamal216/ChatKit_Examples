# app/store.py
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from chatkit.store import Store, AttachmentStore, NotFoundError
from chatkit.types import (
    ThreadMetadata, ThreadItem, Page, Attachment, 
    AttachmentCreateParams, ThreadItemBase
)
from pydantic import TypeAdapter

from .types import RequestContext

DB_PATH = "chatkit.db"

class SQLiteStore(Store[RequestContext], AttachmentStore[RequestContext]):
    def __init__(self):
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY(thread_id) REFERENCES threads(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)

    # --- Thread Operations ---

    async def load_thread(self, thread_id: str, context: RequestContext) -> ThreadMetadata:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data FROM threads WHERE id = ? AND user_id = ?", 
                (thread_id, context.user_id)
            ).fetchone()
            if not row:
                raise NotFoundError(f"Thread {thread_id} not found")
            return ThreadMetadata.model_validate_json(row[0])

    async def save_thread(self, thread: ThreadMetadata, context: RequestContext) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO threads (id, user_id, created_at, data) VALUES (?, ?, ?, ?)",
                (thread.id, context.user_id, thread.created_at.isoformat(), thread.model_dump_json())
            )

    async def load_threads(self, limit: int, after: str | None, order: str, context: RequestContext) -> Page[ThreadMetadata]:
        with self._get_conn() as conn:
            # Simple pagination logic
            query = "SELECT data FROM threads WHERE user_id = ? ORDER BY created_at DESC"
            rows = conn.execute(query, (context.user_id,)).fetchall()
            
            threads = [ThreadMetadata.model_validate_json(r[0]) for r in rows]
            
            # Manual slice for demo purposes (SQL limit/offset is more efficient in prod)
            start_idx = 0
            if after:
                for i, t in enumerate(threads):
                    if t.id == after:
                        start_idx = i + 1
                        break
            
            sliced = threads[start_idx : start_idx + limit]
            has_more = (start_idx + limit) < len(threads)
            new_after = sliced[-1].id if sliced and has_more else None
            
            return Page(data=sliced, has_more=has_more, after=new_after)

    async def delete_thread(self, thread_id: str, context: RequestContext) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM threads WHERE id = ? AND user_id = ?", (thread_id, context.user_id))
            conn.execute("DELETE FROM items WHERE thread_id = ? AND user_id = ?", (thread_id, context.user_id))

    # --- Item Operations ---

    async def load_thread_items(self, thread_id: str, after: str | None, limit: int, order: str, context: RequestContext) -> Page[ThreadItem]:
        with self._get_conn() as conn:
            # Basic validation that thread belongs to user
            thread_row = conn.execute("SELECT 1 FROM threads WHERE id = ? AND user_id = ?", (thread_id, context.user_id)).fetchone()
            if not thread_row:
                raise NotFoundError("Thread not found")

            # Get all items, verify types using TypeAdapter
            rows = conn.execute(
                "SELECT data, created_at FROM items WHERE thread_id = ? ORDER BY created_at ASC", 
                (thread_id,)
            ).fetchall()
            
            # Parse all to sort/filter
            adapter = TypeAdapter(ThreadItem)
            items = [adapter.validate_json(r[0]) for r in rows]
            
            if order == "desc":
                items.reverse()

            start_idx = 0
            if after:
                for i, item in enumerate(items):
                    if item.id == after:
                        start_idx = i + 1
                        break
            
            sliced = items[start_idx : start_idx + limit]
            has_more = (start_idx + limit) < len(items)
            new_after = sliced[-1].id if sliced and has_more else None

            return Page(data=sliced, has_more=has_more, after=new_after)

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: RequestContext) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO items (id, thread_id, user_id, created_at, data) VALUES (?, ?, ?, ?, ?)",
                (item.id, thread_id, context.user_id, item.created_at.isoformat(), item.model_dump_json())
            )

    async def save_item(self, thread_id: str, item: ThreadItem, context: RequestContext) -> None:
        # Same as add for this simple implementation, essentially an upsert
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO items (id, thread_id, user_id, created_at, data) VALUES (?, ?, ?, ?, ?)",
                (item.id, thread_id, context.user_id, item.created_at.isoformat(), item.model_dump_json())
            )

    async def load_item(self, thread_id: str, item_id: str, context: RequestContext) -> ThreadItem:
        with self._get_conn() as conn:
            row = conn.execute("SELECT data FROM items WHERE id = ? AND thread_id = ?", (item_id, thread_id)).fetchone()
            if not row:
                raise NotFoundError(f"Item {item_id} not found")
            return TypeAdapter(ThreadItem).validate_json(row[0])

    async def delete_thread_item(self, thread_id: str, item_id: str, context: RequestContext) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM items WHERE id = ? AND thread_id = ?", (item_id, thread_id))

    # --- Attachment Operations ---

    async def save_attachment(self, attachment: Attachment, context: RequestContext) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO attachments (id, user_id, data) VALUES (?, ?, ?)",
                (attachment.id, context.user_id, attachment.model_dump_json())
            )

    async def load_attachment(self, attachment_id: str, context: RequestContext) -> Attachment:
        with self._get_conn() as conn:
            row = conn.execute("SELECT data FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Attachment {attachment_id} not found")
            return TypeAdapter(Attachment).validate_json(row[0])

    async def delete_attachment(self, attachment_id: str, context: RequestContext) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
    
    # Required by abstract base class, but unused in Direct upload strategy
    # The server manually saves the attachment in main.py
    async def create_attachment(self, input: AttachmentCreateParams, context: RequestContext) -> Attachment:
        raise NotImplementedError("Using direct upload strategy")