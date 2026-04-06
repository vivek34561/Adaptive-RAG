import json
import os
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()


class ChatStoreError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_connection() -> psycopg.Connection[Any]:
    if hasattr(_get_connection, "_connection"):
        connection = _get_connection._connection  # type: ignore[attr-defined]
        if connection and not connection.closed:
            return connection

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ChatStoreError("DATABASE_URL is not configured.")

    try:
        _get_connection._connection = psycopg.connect(  # type: ignore[attr-defined]
            database_url,
            row_factory=dict_row,
            autocommit=True,
        )
        return _get_connection._connection  # type: ignore[attr-defined]
    except Exception as exc:
        raise ChatStoreError(f"Failed to connect to PostgreSQL: {exc}") from exc


def _fetch_one(query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    connection = _get_connection()
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def _fetch_all(query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    connection = _get_connection()
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows or []


def _execute(query: str, params: tuple[Any, ...]) -> None:
    connection = _get_connection()
    with connection.cursor() as cursor:
        cursor.execute(query, params)


def create_session(title: str) -> dict[str, Any]:
    session_title = title[:120] if title else "New chat"
    query = """
        insert into public.chat_sessions (title, last_message_at)
        values (%s, %s)
        returning id::text as id, title, created_at::text as created_at, last_message_at::text as last_message_at
    """
    row = _fetch_one(query, (session_title, _now_iso()))
    if not row:
        raise ChatStoreError("Failed to create chat session.")
    return row


def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    query = """
        select id::text as id, title, created_at::text as created_at, last_message_at::text as last_message_at
        from public.chat_sessions
        order by last_message_at desc
        limit %s
    """
    return _fetch_all(query, (limit,))


def update_session_title(session_id: str, title: str) -> None:
    try:
        _execute(
            "update public.chat_sessions set title = %s where id = %s",
            (title[:120], session_id),
        )
    except Exception as exc:
        raise ChatStoreError(f"Failed to update session title: {exc}") from exc


def append_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query = """
        insert into public.chat_messages (session_id, role, content, metadata)
        values (%s, %s, %s, %s::jsonb)
        returning id::text as id, session_id::text as session_id, role, content, metadata, created_at::text as created_at
    """
    metadata_json = json.dumps(metadata or {})
    row = _fetch_one(query, (session_id, role, content, metadata_json))
    if not row:
        raise ChatStoreError("Failed to append chat message.")

    _execute(
        "update public.chat_sessions set last_message_at = %s where id = %s",
        (_now_iso(), session_id),
    )
    return row


def get_messages(session_id: str, limit: int = 500) -> list[dict[str, Any]]:
    query = """
        select id::text as id, session_id::text as session_id, role, content, metadata, created_at::text as created_at
        from public.chat_messages
        where session_id = %s
        order by created_at asc
        limit %s
    """
    return _fetch_all(query, (session_id, limit))
