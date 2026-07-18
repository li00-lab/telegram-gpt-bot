import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import load_settings
from .handlers import ConversationStore, handle_mention, handle_start
from .openai_client import OpenAIStreamer

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    settings = load_settings()
    application = Application.builder().token(settings.telegram_token).build()

    application.bot_data["settings"] = settings
    application.bot_data["streamer"] = OpenAIStreamer(
        settings.openai_api_key, settings.openai_model
    )
    application.bot_data["store"] = ConversationStore(settings.history_limit)

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("help", handle_start))

    group_mention_filter = filters.TEXT & filters.Entity("mention") & ~filters.COMMAND
    dm_filter = filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND
    application.add_handler(MessageHandler(group_mention_filter, handle_mention))
    application.add_handler(MessageHandler(dm_filter, handle_mention))

    return application


def main() -> None:
    application = build_application()
    settings = application.bot_data["settings"]

    if settings.webhook_url:
        logger.info("Starting bot in webhook mode at %s", settings.webhook_url)
        application.run_webhook(
            listen="0.0.0.0",
            port=settings.webhook_port,
            url_path=settings.telegram_token,
            webhook_url=f"{settings.webhook_url.rstrip('/')}/{settings.telegram_token}",
        )
    else:
        logger.info("Starting bot in polling mode")
        application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
