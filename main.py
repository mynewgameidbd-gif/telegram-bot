"""
Main — দুই বট একসাথে একই প্রসেসে চালাবে
User Bot + Admin Bot একই SQLite DB শেয়ার করবে
"""
import asyncio
import logging
from database import init_db
from user_bot import build_user_app, notification_worker
from admin_bot import build_admin_app

# ═══ Logging ═══
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_both_bots():
    """দুই বট একসাথে চালাও"""
    init_db()

    logger.info("⏳ Application তৈরি হচ্ছে...")
    user_app = build_user_app()
    admin_app = build_admin_app()

    logger.info("⏳ Initialize হচ্ছে...")
    await user_app.initialize()
    await admin_app.initialize()

    logger.info("⏳ Start হচ্ছে...")
    await user_app.start()
    await admin_app.start()

    logger.info("⏳ Polling শুরু...")
    await user_app.updater.start_polling(drop_pending_updates=True)
    await admin_app.updater.start_polling(drop_pending_updates=True)

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🤖✅ দুই বট চালু হয়েছে!")
    logger.info("👤 User Bot  → Running")
    logger.info("👑 Admin Bot → Running")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Forever চলতে থাকবে
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 বন্ধ করা হচ্ছে...")
        await user_app.updater.stop()
        await admin_app.updater.stop()
        await user_app.stop()
        await admin_app.stop()
        await user_app.shutdown()
        await admin_app.shutdown()


def main():
    try:
        asyncio.run(run_both_bots())
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
