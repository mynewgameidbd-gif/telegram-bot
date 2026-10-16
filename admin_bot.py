"""
Admin Bot — অ্যাডমিনের জন্য
- ক্যাটাগরি ম্যানেজমেন্ট
- রিপোর্ট আপলোড (অটো প্রসেস)
- সাবমিশন রিসিভ
- পরিসংখ্যান
"""
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from config import ADMIN_BOT_TOKEN, ADMIN_ID
from database import (
    init_db, add_category, get_all_categories, get_category, delete_category,
    update_category_columns, rename_category, add_subcategory,
    get_subcategories, get_subcategory, delete_subcategory,
    update_subcategory_rate, get_user, get_stats, queue_notification,
    process_report_detailed
)
from file_processor import parse_report
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

# Conversation States
(ADD_CAT_NAME, ADD_CAT_COLUMNS,
 ADD_SUB_NAME, ADD_SUB_RATE,
 RENAME_CAT, EDIT_COLUMNS) = range(6)


def admin_menu():
    kb = [
        [KeyboardButton("📁 ক্যাটাগরি ম্যানেজ"), KeyboardButton("📤 রিপোর্ট আপলোড")],
        [KeyboardButton("📊 পরিসংখ্যান")],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def back_kb():
    return ReplyKeyboardMarkup([["🔙 মেইন মেনু"]], resize_keyboard=True)


# ═══════════════════════════════════════
#  /start
# ═══════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ আপনি অ্যাডমিন নন।")
        return
    await update.message.reply_text(
        "👑 **অ্যাডমিন প্যানেল**\n\nনিচের মেনু থেকে অপশন বেছে নিন 👇",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )


# ═══════════════════════════════════════
#  📁 ক্যাটাগরি ম্যানেজ
# ═══════════════════════════════════════
async def cat_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    cats = get_all_categories(active_only=False)
    keyboard = []
    for c in cats:
        subs = get_subcategories(c[0], active_only=False)
        keyboard.append([InlineKeyboardButton(
            f"📁 {c[1]} ({len(subs)} সাব)", callback_data=f"cat_{c[0]}"
        )])
    keyboard.append([InlineKeyboardButton("➕ নতুন ক্যাটাগরি", callback_data="add_cat")])
    await update.message.reply_text(
        "📁 **ক্যাটাগরি ম্যানেজমেন্ট**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cat_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[1])
    cat = get_category(cat_id)
    if not cat:
        await query.edit_message_text("❌ ক্যাটাগরি পাওয়া যায়নি।")
        return

    subs = get_subcategories(cat_id, active_only=False)
    text = f"📁 **{cat[1]}**\n📋 কলাম: `{cat[2]}`\n\n"
    if subs:
        text += "**সাব-ক্যাটাগরি:**\n"
        for s in subs:
            text += f"• {s[1]} — ৳{s[2]}\n"
    else:
        text += "_কোনো সাব-ক্যাটাগরি নেই_\n"

    keyboard = [
        [InlineKeyboardButton("➕ নতুন সাব যোগ", callback_data=f"addsub_{cat_id}")],
        [InlineKeyboardButton("✏️ নাম পরিবর্তন", callback_data=f"rename_{cat_id}")],
        [InlineKeyboardButton("📋 কলাম পরিবর্তন", callback_data=f"cols_{cat_id}")],
        [InlineKeyboardButton("🗑️ ক্যাটাগরি ডিলিট", callback_data=f"delcat_{cat_id}")],
        [InlineKeyboardButton("🔙 ফিরে যান", callback_data="back_cats")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))


# ═══════════════════════════════════════
#  নতুন ক্যাটাগরি
# ═══════════════════════════════════════
async def add_cat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📝 **নতুন ক্যাটাগরির নাম লিখুন**\n\nউদাহরণ: `Facebook`",
        parse_mode="Markdown",
        reply_markup=back_kb()
    )
    return ADD_CAT_NAME


async def add_cat_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🔙 মেইন মেনু":
        await update.message.reply_text("মেইন মেনু", reply_markup=admin_menu())
        return ConversationHandler.END
    context.user_data["new_cat_name"] = text
    await update.message.reply_text(
        "📋 **কলাম স্ট্রাকচার লিখুন**\n\n"
        "উদাহরণ: `Uid, Password, Cookies`\n"
        "কমা দিয়ে আলাদা করুন।",
        parse_mode="Markdown",
        reply_markup=back_kb()
    )
    return ADD_CAT_COLUMNS


async def add_cat_columns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🔙 মেইন মেনু":
        await update.message.reply_text("মেইন মেনু", reply_markup=admin_menu())
        return ConversationHandler.END
    name = context.user_data["new_cat_name"]
    if add_category(name, text):
        await update.message.reply_text(
            f"✅ ক্যাটাগরি **{name}** যোগ হয়েছে!\n📋 কলাম: `{text}`",
            parse_mode="Markdown", reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text(
            f"❌ ক্যাটাগরি **{name}** আগে থেকেই আছে!",
            parse_mode="Markdown", reply_markup=admin_menu()
        )
    return ConversationHandler.END


# ═══════════════════════════════════════
#  সাব-ক্যাটাগরি
# ═══════════════════════════════════════
async def addsub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[1])
    context.user_data["cat_id"] = cat_id
    await query.message.reply_text(
        "📝 **সাব-ক্যাটাগরির নাম লিখুন**\n\nউদাহরণ: `FB Cookies`",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return ADD_SUB_NAME


async def addsub_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🔙 মেইন মেনু":
        await update.message.reply_text("মেইন মেনু", reply_markup=admin_menu())
        return ConversationHandler.END
    context.user_data["sub_name"] = text
    await update.message.reply_text(
        "💰 **রেট লিখুন (প্রতি আইডিতে)**\n\nউদাহরণ: `4.2`",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return ADD_SUB_RATE


async def addsub_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🔙 মেইন মেনু":
        await update.message.reply_text("মেইন মেনু", reply_markup=admin_menu())
        return ConversationHandler.END
    try:
        rate = float(text)
    except:
        await update.message.reply_text("❌ শুধু সংখ্যা লিখুন। যেমন: `4.2`", parse_mode="Markdown")
        return ADD_SUB_RATE
    cat_id = context.user_data["cat_id"]
    sub_name = context.user_data["sub_name"]
    add_subcategory(cat_id, sub_name, rate)
    await update.message.reply_text(
        f"✅ **{sub_name}** যোগ হয়েছে!\n💰 রেট: ৳{rate}",
        parse_mode="Markdown", reply_markup=admin_menu()
    )
    return ConversationHandler.END


# ═══════════════════════════════════════
#  রিনেম / কলাম
# ═══════════════════════════════════════
async def rename_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[1])
    context.user_data["rename_cat_id"] = cat_id
    await query.message.reply_text("✏️ **নতুন নাম লিখুন:**", reply_markup=back_kb())
    return RENAME_CAT


async def rename_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🔙 মেইন মেনু":
        await update.message.reply_text("মেইন মেনু", reply_markup=admin_menu())
        return ConversationHandler.END
    cat_id = context.user_data["rename_cat_id"]
    rename_category(cat_id, text)
    await update.message.reply_text(f"✅ নাম: **{text}**", parse_mode="Markdown",
                                     reply_markup=admin_menu())
    return ConversationHandler.END


async def cols_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[1])
    context.user_data["cols_cat_id"] = cat_id
    await query.message.reply_text(
        "📋 **নতুন কলাম লিখুন:**\n\nউদাহরণ: `Uid, Password, Cookies`",
        parse_mode="Markdown", reply_markup=back_kb()
    )
    return EDIT_COLUMNS


async def cols_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🔙 মেইন মেনু":
        await update.message.reply_text("মেইন মেনু", reply_markup=admin_menu())
        return ConversationHandler.END
    cat_id = context.user_data["cols_cat_id"]
    update_category_columns(cat_id, text)
    await update.message.reply_text(f"✅ কলাম: `{text}`", parse_mode="Markdown",
                                     reply_markup=admin_menu())
    return ConversationHandler.END


# ═══════════════════════════════════════
#  Callback Router
# ═══════════════════════════════════════
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "back_cats":
        await query.answer()
        cats = get_all_categories(active_only=False)
        keyboard = []
        for c in cats:
            subs = get_subcategories(c[0], active_only=False)
            keyboard.append([InlineKeyboardButton(
                f"📁 {c[1]} ({len(subs)} সাব)", callback_data=f"cat_{c[0]}"
            )])
        keyboard.append([InlineKeyboardButton("➕ নতুন ক্যাটাগরি", callback_data="add_cat")])
        await query.edit_message_text(
            "📁 **ক্যাটাগরি ম্যানেজমেন্ট**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("cat_"):
        await cat_detail(update, context)
        return

    if data.startswith("delcat_"):
        cat_id = int(data.split("_")[1])
        kb = [[
            InlineKeyboardButton("✅ হ্যাঁ ডিলিট", callback_data=f"confirmdel_{cat_id}"),
            InlineKeyboardButton("❌ না", callback_data="back_cats")
        ]]
        await query.edit_message_text(
            "⚠️ **নিশ্চিত?** সব সাব-ক্যাটাগরি ডিলিট হবে!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        await query.answer()
        return

    if data.startswith("confirmdel_"):
        cat_id = int(data.split("_")[1])
        delete_category(cat_id)
        await query.edit_message_text("✅ ক্যাটাগরি ডিলিট হয়েছে।")
        await query.answer()
        return

    await query.answer()


# ═══════════════════════════════════════
#  📤 রিপোর্ট আপলোড
# ═══════════════════════════════════════
async def report_upload_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "📤 **রিপোর্ট আপলোড**\n\n"
        "➤ Excel ফাইল (.xlsx) আপলোড করুন\n\n"
        "**ফরম্যাট:**\n"
        "• কলাম A: Uid / Username\n"
        "• কলাম C: `ok` অথবা `of`\n\n"
        "📌 `ok` = ভালো (টাকা যোগ হবে)\n"
        "📌 `of` = নষ্ট (টাকা হবে না)\n\n"
        "⚠️ আপলোডের সাথে সাথে সব ইউজারের হিসাব হবে!",
        parse_mode="Markdown"
    )


async def handle_report_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message
    if not msg.document:
        return

    doc = msg.document
    await msg.reply_text("⏳ রিপোর্ট প্রসেস হচ্ছে...")

    try:
        file = await context.bot.get_file(doc.file_id)
        local_path = f"/tmp/report_{doc.file_name}"
        await file.download_to_drive(local_path)
    except Exception as e:
        await msg.reply_text(f"❌ ডাউনলোড error: {e}")
        return

    report_data = parse_report(local_path, doc.file_name)
    if not report_data:
        await msg.reply_text("❌ রিপোর্টে কোনো ডেটা পাওয়া যায়নি।")
        try:
            os.remove(local_path)
        except:
            pass
        return

    total_ok = sum(1 for v in report_data.values() if v == "ok")
    total_of = sum(1 for v in report_data.values() if v == "of")

    detail_results = process_report_detailed(report_data)

    # প্রতিটা আইডির জন্য নোটিফিকেশন কিউ
    queued = 0
    for user_id, data in detail_results.items():
        for uid, status in data["results"]:
            if status == "ok":
                msg_text = f"✅ `{uid}`\n\nআপনার এই কাজটি অ্যাপ্রুভ হয়েছে।"
            else:
                msg_text = f"❌ `{uid}`\n\nআপনার এই আইডিটি রিজেক্ট হয়েছে।"
            queue_notification(user_id, msg_text)
            queued += 1

        summary = (
            f"📊 **আপনার রিপোর্ট সামারি**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📁 {data['category']} — {data['subcategory']}\n\n"
            f"✅ ভালো: **{data['good']}টি**\n"
            f"❌ নষ্ট: **{data['bad']}টি**\n"
            f"💰 রেট: ৳{data['rate']}/আইডি\n"
            f"💵 **আয়: ৳{data['earning']:.2f}**\n\n"
            f"ব্যালেন্সে যোগ করা হয়েছে ✅"
        )
        queue_notification(user_id, summary)
        queued += 1

    summary_text = (
        f"✅ **রিপোর্ট প্রসেস সম্পন্ন!**\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 মোট আইডি: {len(report_data)}\n"
        f"• ✅ ভালো: {total_ok}\n"
        f"• ❌ নষ্ট: {total_of}\n"
        f"• 👥 ইউজার: {len(detail_results)}\n"
        f"• 📨 কিউ: {queued} নোটিফিকেশন\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for user_id, data in list(detail_results.items())[:10]:
        u = get_user(user_id)
        uname = u[2] if u else f"ID:{user_id}"
        summary_text += (
            f"👤 {uname}\n"
            f"   ✅{data['good']} ❌{data['bad']} 💰৳{data['earning']:.2f}\n"
        )

    await msg.reply_text(summary_text, parse_mode="Markdown")

    try:
        os.remove(local_path)
    except:
        pass


# ═══════════════════════════════════════
#  📊 পরিসংখ্যান
# ═══════════════════════════════════════
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    s = get_stats()
    await update.message.reply_text(
        f"📊 **পরিসংখ্যান**\n\n"
        f"📥 মোট সাবমিশন: {s['total_sub']}\n"
        f"🔢 মোট আইডি: {s['total_acc']}\n"
        f"👥 মোট ইউজার: {s['users']}\n"
        f"⏳ পেন্ডিং সাবমিশন: {s['pending_sub']}\n"
        f"💸 পেন্ডিং উইথড্র: {s['pending_wd']}",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )


# ═══════════════════════════════════════
#  BUILD ADMIN APP
# ═══════════════════════════════════════
def build_admin_app():
    """Admin Bot Application বানায় (main.py থেকে কল হবে)"""
    app = ApplicationBuilder().token(ADMIN_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(MessageHandler(filters.Regex("^📁 ক্যাটাগরি ম্যানেজ$"), cat_manage))
    app.add_handler(MessageHandler(filters.Regex("^📊 পরিসংখ্যান$"), stats))
    app.add_handler(MessageHandler(filters.Regex("^📤 রিপোর্ট আপলোড$"), report_upload_prompt))

    # Report file (শুধু Admin থেকে)
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
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    ))

    # Conversation: Add Subcategory
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(addsub_start, pattern="^addsub_")],
        states={
            ADD_SUB_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsub_name)],
            ADD_SUB_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsub_rate)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    ))

    # Conversation: Rename
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(rename_start, pattern="^rename_")],
        states={RENAME_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rename_handler)]},
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    ))

    # Conversation: Edit Columns
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cols_start, pattern="^cols_")],
        states={EDIT_COLUMNS: [MessageHandler(filters.TEXT & ~filters.COMMAND, cols_handler)]},
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    ))

    # Other callbacks
    app.add_handler(CallbackQueryHandler(callback_router))

    return app


# Local testing
if __name__ == "__main__":
    init_db()
    app = build_admin_app()
    logger.info("👑 Admin Bot চালু...")
    app.run_polling(drop_pending_updates=True)
