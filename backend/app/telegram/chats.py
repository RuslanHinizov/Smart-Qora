"""Telegram chat registry.

Authorisation is the comma-separated list in ``AppSettings.telegram_chat_id`` —
the dashboard is the single control point for who may use the bot and receive
alerts. ``telegram_chats`` rows only carry each chat's language preference
(set with ``/dil``), defaulting to Russian.
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSettings, TelegramChat

DEFAULT_LANG = "ru"
LANGS = ("ru", "kk", "en", "tr")


def parse_chat_ids(raw: str) -> list[str]:
    return [c for c in re.split(r"[\s,;]+", raw or "") if c]


async def authorized_chat_ids(session: AsyncSession) -> set[str]:
    row = await session.get(AppSettings, 1)
    return set(parse_chat_ids(row.telegram_chat_id if row else ""))


async def is_authorized(session: AsyncSession, chat_id: str) -> bool:
    return str(chat_id) in await authorized_chat_ids(session)


async def chat_language(session: AsyncSession, chat_id: str) -> str:
    row = await session.get(TelegramChat, str(chat_id))
    return row.language if row else DEFAULT_LANG


async def set_chat_language(session: AsyncSession, chat_id: str, language: str) -> None:
    row = await session.get(TelegramChat, str(chat_id))
    if row is None:
        session.add(TelegramChat(chat_id=str(chat_id), language=language))
    else:
        row.language = language
    await session.commit()


async def recipients(session: AsyncSession) -> list[tuple[str, str]]:
    """(chat_id, language) for every authorised chat — used for every outgoing message."""
    ids = await authorized_chat_ids(session)
    if not ids:
        return []
    langs = dict((await session.execute(
        select(TelegramChat.chat_id, TelegramChat.language))).all())
    return [(cid, langs.get(cid, DEFAULT_LANG)) for cid in sorted(ids)]
