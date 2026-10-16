"""
Main — দুই বট একসাথে চালাবে (Shared DB)
Render এ একটাই worker এ এটা চালাতে হবে।
"""
import asyncio
import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ConversationHandler
)
from config import USER_BOT_TOKEN, ADMIN_BOT_TOKEN, ADMIN_ID
from database import init_db

# ============ USER BOT HANDLERS ============
from user_bot import (
    start as u_start, file_submit, balance, my_report,
    withdraw_start, withdraw_handle, support_start, support_handle,
    handle_document, user_cat_click, user_sub_click,
    user_cancel, noop, notification_worker, main_menu, back_kb
)

# ============ ADMIN BOT HANDLERS ============
from admin_bot import (
    start as a_start, stats as a_stats, cat_manage,
    report_upload_prompt, handle_report_file,
    add_cat_start, add_cat_name, add_cat_columns,
    addsub_start, addsub_name, addsub_rate,
    rename_start, rename_handler,
    cols_start, cols_handler, callback_router,
    ADD_CAT_NAME, ADD_CAT_COLUMNS, ADD_SUB_NAME,
    ADD_SUB_RATE, RENAME_CAT, EDIT_COLUMNS,
    admin_menu, back_kb as admin_back_kb
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def build_user_app():
    app = ApplicationBuilder().token(USER_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", u_start))
    app.add_handler(MessageHandler(filters.Regex("^📊 ফাইল সাবমিট$"), file_submit))
    app.add_handler(MessageHandler(filters.Regex("^💵 ব্যালেন্স$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^📋 আমার রিপোর্ট$"), my_report))
    app.add_handler(MessageHandler(filters.Regex("^💸 উইথড্র$"), withdraw_start))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ সাপোর্ট$"), support_start))

    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.User(ADMIN_ID), handle_document))

    app.add_handler(CallbackQueryHandler(user_cat_click, pattern="^ucat_"))
    app.add_handler(CallbackQueryHandler(user_sub_click, pattern="^usub_"))
    app.add_handler(CallbackQueryHandler(user_cancel, pattern="^ucancel$"))
    app.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🔙 মেইন মেনু$"),
        support_handle
    ))

    # Notification worker
    app.job_queue.run_repeating(notification_worker, interval=3, first=5)

    return app


def build_admin_app():
    app = ApplicationBuilder().token(ADMIN_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", a_start))
    app.add_handler(CommandHandler("stats", a_stats))

    app.add_handler(MessageHandler(filters.Regex("^📁 ক্যাটাগরি ম্যানেজ$"), cat_manage))
    app.add_handler(MessageHandler(filters.Regex("^📊 পরিসংখ্যান$"), a_stats))
    app.add_handler(MessageHandler(filters.Regex("^📤 রিপোর্ট আপলোড$"), report_upload_prompt))

    # Report file (only from admin)
    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.User(ADMIN_ID),
        handle_report_file
    ))

    # Conversation: Add Category
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(add_cat_start, pattern="^add_cat$")],
        states={
            ADD_CAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_name)],
            ADD_CAT_COLUMNS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_columns)],
        },
        fallbacks=[CommandHandler("start", a_start)],
        per_message=False,
    ))

    # Conversation: Add Subcategory
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(addsub_start, pattern="^addsub_")],
        states={
            ADD_SUB_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsub_name)],
            ADD_SUB_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsub_rate)],
        },
        fallbacks=[CommandHandler("start", a_start)],
        per_message=False,
    ))

    # Conversation: Rename
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(rename_start, pattern="^rename_")],
        states={RENAME_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rename_handler)]},
        fallbacks=[CommandHandler("start", a_start)],
        per_message=False,
    ))

    # Conversation: Edit Columns
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cols_start, pattern="^cols_")],
        states={EDIT_COLUMNS: [MessageHandler(filters.TEXT & ~filters.COMMAND, cols_handler)]},
        fallbacks=[CommandHandler("start", a_start)],
        per_message=False,
    ))

    # Other callbacks
    app.add_handler(CallbackQueryHandler(callback_router))

    return app


async def run_both():
    init_db()

    user_app = build_user_app()
    admin_app = build_admin_app()

    # initialize
    await user_app.initialize()
    await admin_app.initialize()
    await user_app.start()
    await admin_app.start()

    # start polling
    await user_app.updater.start_polling(drop_pending_updates=True)
    await admin_app.updater.start_polling(drop_pending_updates=True)

    logger.info("=" * 50)
    logger.info("🤖 দুই বট একসাথে চালু হয়েছে!")
    logger.info(f"👤 User Bot: active")
    logger.info(f"👑 Admin Bot: active (ID: {ADMIN_ID})")
    logger.info("=" * 50)

    # Forever
    stop_event = asyncio.Event()
    await stop_event.wait()


def main():
    try:
        asyncio.run(run_both())
    except (KeyboardInterrupt, SystemExit):
        logger.info("বট বন্ধ করা হচ্ছে...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
