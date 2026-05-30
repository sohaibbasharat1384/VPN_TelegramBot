"""Minimal Telegram Bot API client (httpx).

Used by Celery workers and broadcast jobs to push messages without pulling in the
full aiogram dispatcher. The bots themselves use aiogram for interactive flows.
"""
from __future__ import annotations

import httpx

from app.core.logging import get_logger

logger = get_logger("telegram")
_API = "https://api.telegram.org"


async def send_message(
    token: str, chat_id: int, text: str, *, parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
) -> bool:
    url = f"{_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code == 200 and resp.json().get("ok"):
            return True
        logger.warning("telegram_send_failed", chat_id=chat_id, status=resp.status_code, body=resp.text[:200])
        return False
    except httpx.HTTPError as exc:
        logger.warning("telegram_send_error", chat_id=chat_id, error=str(exc))
        return False


async def send_photo(token: str, chat_id: int, photo: bytes, *, caption: str = "") -> bool:
    return await _send_file(token, chat_id, "sendPhoto", "photo", "image.png", photo, caption)


async def send_document(token: str, chat_id: int, data: bytes, filename: str, *, caption: str = "") -> bool:
    return await _send_file(token, chat_id, "sendDocument", "document", filename, data, caption)


async def send_video(token: str, chat_id: int, data: bytes, *, caption: str = "") -> bool:
    return await _send_file(token, chat_id, "sendVideo", "video", "video.mp4", data, caption)


async def _send_file(
    token: str, chat_id: int, method: str, field: str, filename: str, data: bytes, caption: str
) -> bool:
    url = f"{_API}/bot{token}/{method}"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                data={"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"},
                files={field: (filename, data)},
            )
        return resp.status_code == 200 and resp.json().get("ok", False)
    except httpx.HTTPError as exc:
        logger.warning("telegram_file_error", chat_id=chat_id, method=method, error=str(exc))
        return False
