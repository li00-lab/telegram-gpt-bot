import logging
import re
import time
from collections import defaultdict, deque

from telegram import Update
from telegram.constants import ChatAction, ChatType, ParseMode
from telegram.ext import ContextTypes

from .config import Settings
from .openai_client import OpenAIStreamer

logger = logging.getLogger(__name__)

EDIT_INTERVAL_SECONDS = 1.2
MAX_TELEGRAM_MESSAGE_LENGTH = 4096


class ConversationStore:
    """Keeps a short in-memory rolling history per chat (lost on restart)."""

    def __init__(self, history_limit: int) -> None:
        self._chats: dict[int, deque[dict]] = defaultdict(
            lambda: deque(maxlen=history_limit)
        )

    def append(self, chat_id: int, role: str, content: str) -> None:
        self._chats[chat_id].append({"role": role, "content": content})

    def get(self, chat_id: int) -> list[dict]:
        return list(self._chats[chat_id])


def extract_question(update: Update, bot_username: str) -> str | None:
    message = update.effective_message
    if message is None or not message.text:
        return None

    if update.effective_chat and update.effective_chat.type == ChatType.PRIVATE:
        return message.text.strip() or None

    pattern = re.compile(rf"@{re.escape(bot_username)}", re.IGNORECASE)
    if not pattern.search(message.text):
        return None

    question = pattern.sub("", message.text, count=1).strip()
    if not question and message.reply_to_message and message.reply_to_message.text:
        question = message.reply_to_message.text

    return question or None


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_username = context.bot.username
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        f"Hi! Add me to a group and mention me like `@{bot_username} your question` "
        "to get an answer. You can also message me directly here.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    streamer: OpenAIStreamer = context.bot_data["streamer"]
    store: ConversationStore = context.bot_data["store"]

    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    question = extract_question(update, context.bot.username)
    if not question:
        return

    await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)

    store.append(chat.id, "user", question)

    sent_message = await message.reply_text("...", reply_to_message_id=message.message_id)

    buffer = ""
    last_edit = 0.0
    try:
        async for delta in streamer.stream_reply(settings.system_prompt, store.get(chat.id)):
            buffer += delta
            now = time.monotonic()
            if now - last_edit >= EDIT_INTERVAL_SECONDS:
                await _safe_edit(context, chat.id, sent_message.message_id, buffer)
                last_edit = now
        await _safe_edit(
            context,
            chat.id,
            sent_message.message_id,
            buffer or "I don't have a response for that.",
        )
    except Exception:
        logger.exception("OpenAI streaming failed")
        await _safe_edit(
            context,
            chat.id,
            sent_message.message_id,
            "Sorry, something went wrong talking to OpenAI.",
        )
        return

    store.append(chat.id, "assistant", buffer)


async def _safe_edit(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, text: str
) -> None:
    text = text[:MAX_TELEGRAM_MESSAGE_LENGTH]
    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
    except Exception as exc:
        if "not modified" not in str(exc).lower():
            logger.warning("Failed to edit message: %s", exc)
