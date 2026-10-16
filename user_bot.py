"""
User Bot — ইউজারদের জন্য
- ফাইল সাবমিট, ব্যালেন্স, উইথড্র, রিপোর্ট, সাপোর্ট
- Background Notification Worker
"""
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from config import USER_BOT_TOKEN, ADMIN_ID
from database import (
    init_db, add_user, get_user, get_all_categories, get_category,
    get_subcategories, get_subcategory, save_submission, get_user_report,
    get_pending_notifications, mark_notification_sent, save_withdrawal
)
from file_processor import extract_uids
from datetime import datetime
import os
import asyncio
import logging

logger = logging.getLogger(__name__)


def main_menu():
    kb = [
        [KeyboardButton("📊 ফাইল সাবমিট"), KeyboardButton("💵 ব্যালেন্স")],
        [KeyboardButton("💸 উইথড্র"), KeyboardButton("📋 আমার রিপোর্ট")],
        [KeyboardButton("ℹ️ সাপোর্ট")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def back_kb():
    return ReplyKeyboardMarkup([["🔙 মেইন মেনু"]], resize_keyboard=True)


# ═══════════════════════════════════════
#  /start
# ═══════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user)
    await update.message.reply_text(
        f"👋 হ্যালো {update.effective_user.first_name}!\n\n"
        "🤖 Instagram Submission Bot-এ স্বাগতম।\n"
        "নিচের মেনু থেকে অপশন বেছে নিন 👇",
        reply_markup=main_menu()
    )


# ═══════════════════════════════════════
#  📊 ফাইল সাবমিট
# ═══════════════════════════════════════
async def file_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = get_all_categories()
    if not cats:
        await update.message.reply_text("❌ এখনো কোনো কাজ যোগ করা হয়নি।")
        return

    keyboard = []
    for c in cats:
        keyboard.append([InlineKeyboardButton(f"📁 {c[1]}", callback_data=f"ucat_{c[0]}")])

    await update.message.reply_text(
        "🔥 **যেকোনো একটি কাজ সিলেক্ট করুন** 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def user_cat_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[1])
    cat = get_category(cat_id)
    subs = get_subcategories(cat_id)

    if not subs:
        await query.edit_message_text("❌ এই ক্যাটাগরিতে কোনো কাজ নেই।")
        return

    text = f"**{cat[1]} এর কাজের ধরন:**\n\n"
    for s in subs:
        text += f"• {s[1]} → ৳{s[2]}\n"

    keyboard = []
    for s in subs:
        keyboard.append([InlineKeyboardButton(
            f"🔥 {s[1]} ({s[2]}TK)", callback_data=f"usub_{s[0]}"
        )])
    keyboard.append([InlineKeyboardButton("❌ বাতিল", callback_data="ucancel")])

    await query.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))


async def user_sub_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sub_id = int(query.data.split("_")[1])
    sub = get_subcategory(sub_id)
    cat = get_category(sub[1])

    context.user_data["selected_cat"] = cat
    context.user_data["selected_sub"] = sub

    today = datetime.now().strftime("%Y-%m-%d")
    columns = cat[2].split(",")
    col_text = "\n".join([f"{chr(65+i)}. {c.strip()}" for i, c in enumerate(columns)])

    text = (
        f"📁 **{cat[1]} সাবমিট**\n"
        f"📅 ডেট: {today}\n\n"
        f"➤ অনুগ্রহ করে আপনার `.xlsx` ফাইলটি আপলোড করুন, যেখানে:\n\n"
        f"{col_text}"
    )

    keyboard = [
        [InlineKeyboardButton(f"🔥 {sub[1]} ({sub[2]}TK)", callback_data="noop")],
        [InlineKeyboardButton("❌ বাতিল", callback_data="ucancel")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))


async def user_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ বাতিল করা হয়েছে।")


async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


# ═══════════════════════════════════════
#  ফাইল রিসিভ
# ═══════════════════════════════════════
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    cat = context.user_data.get("selected_cat")
    sub = context.user_data.get("selected_sub")
    if not cat or not sub:
        await msg.reply_text("⚠️ আগে '📊 ফাইল সাবমিট' থেকে শুরু করুন।")
        return

    if not msg.document:
        await msg.reply_text("❌ শুধু ফাইল পাঠান।")
        return

    doc = msg.document
    await msg.reply_text("⏳ ফাইল প্রসেস হচ্ছে...")

    try:
        file = await context.bot.get_file(doc.file_id)
        local_path = f"/tmp/user_{user.id}_{doc.file_name}"
        await file.download_to_drive(local_path)
    except Exception as e:
        await msg.reply_text(f"❌ ফাইল ডাউনলোডে সমস্যা: {e}")
        return

    uids = extract_uids(local_path, doc.file_name)
    count = len(uids)

    if count == 0:
        await msg.reply_text("❌ ফাইলে কোনো Uid পাওয়া যায়নি।")
        try:
            os.remove(local_path)
        except:
            pass
        return

    preview = "\n".join(uids[:10])
    submission_id = save_submission(user, cat, sub, doc.file_name, doc.file_id,
                                     count, preview, uids)

    pending_earning = count * sub[2]

    await msg.reply_text(
        f"✅ **ফাইল গ্রহণ করা হয়েছে!**\n\n"
        f"📁 ক্যাটাগরি: {cat[1]}\n"
        f"🔥 কাজ: {sub[1]}\n"
        f"💰 রেট: ৳{sub[2]} / আইডি\n"
        f"🔢 মোট আইডি: **{count}টি**\n"
        f"💵 সম্ভাব্য আয়: ৳{pending_earning:.2f}\n\n"
        f"⏳ রিভিউতে আছে: **{count}টি আইডি**\n"
        f"💵 পেন্ডিং টাকা: ৳{pending_earning:.2f}\n\n"
        f"📌 অ্যাডমিন রিপোর্ট আপলোড করলে স্বয়ংক্রিয়ভাবে হিসাব হবে।",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

    # অ্যাডমিন বটে পাঠাও
    preview_text = "\n".join([f"`{a}`" for a in uids[:10]])
    caption = (
        f"📥 **নতুন সাবমিশন**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {user.full_name}\n"
        f"🔗 @{user.username or 'N/A'}\n"
        f"📱 `{user.id}`\n"
        f"📁 {cat[1]}\n"
        f"🔥 {sub[1]} (৳{sub[2]})\n"
        f"📄 `{doc.file_name}`\n"
        f"🔢 আইডি: **{count}টি**\n"
        f"💵 সম্ভাব্য: ৳{pending_earning:.2f}\n"
        f"🆔 Sub ID: `{submission_id}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📝 প্রথম ১০টি:\n{preview_text}"
    )

    try:
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=doc.file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Admin notify error: {e}")

    try:
        os.remove(local_path)
    except:
        pass


# ═══════════════════════════════════════
#  💵 ব্যালেন্স
# ═══════════════════════════════════════
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    row = get_user(user.id)
    if not row:
        await update.message.reply_text("আগে /start দিন।")
        return

    (uid, uname, fname, bal, pending_bal,
     total_income, total_withdrawn, completed, in_review) = row

    text = (
        f"💵 **আপনার ব্যালেন্স**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 ব্যালেন্স: {bal:.2f} BDT\n"
        f"💸 পেন্ডিং (উইথড্র): 0.00 BDT\n"
        f"⏳ কাজের পেন্ডিং টাকা: {pending_bal:.2f} BDT\n"
        f"💰 মোট ইনকাম: {total_income:.2f} BDT\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✔️ সম্পন্ন কাজ: {completed} টি\n"
        f"⏳ রিভিউতে আছে: {in_review} টি"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu())


# ═══════════════════════════════════════
#  📋 আমার রিপোর্ট
# ═══════════════════════════════════════
async def my_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rows = get_user_report(user.id)

    if not rows:
        await update.message.reply_text(
            "📋 এখনো কোনো রিপোর্ট নেই।\n"
            "অ্যাডমিন রিপোর্ট আপলোড করলে এখানে দেখা যাবে।",
            reply_markup=main_menu()
        )
        return

    good = [r for r in rows if r[1] == "ok"]
    bad = [r for r in rows if r[1] == "of"]

    text = (
        f"📋 **আপনার রিপোর্ট**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ ভালো: {len(good)}টি\n"
        f"❌ নষ্ট: {len(bad)}টি\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    if good:
        text += "**✅ ভালো আইডি:**\n"
        for r in good[:20]:
            text += f"`{r[0]}`\n"
        if len(good) > 20:
            text += f"... আরও {len(good)-20}টি\n"

    if bad:
        text += "\n**❌ নষ্ট আইডি:**\n"
        for r in bad[:20]:
            text += f"`{r[0]}`\n"
        if len(bad) > 20:
            text += f"... আরও {len(bad)-20}টি\n"

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu())


# ═══════════════════════════════════════
#  💸 উইথড্র
# ═══════════════════════════════════════
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = get_user(update.effective_user.id)
    bal = row[3] if row else 0
    await update.message.reply_text(
        f"💸 **উইথড্র রিকোয়েস্ট**\n\n"
        f"💰 ব্যালেন্স: ৳{bal:.2f}\n\n"
        f"ফরম্যাটে লিখুন:\n"
        f"`বিকাশ, 01712345678, 500`",
        parse_mode="Markdown",
        reply_markup=back_kb()
    )


async def withdraw_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if text == "🔙 মেইন মেনু":
        await update.message.reply_text("মেইন মেনু", reply_markup=main_menu())
        return

    try:
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 3:
            raise ValueError
        method, number, amount = parts[0], parts[1], float(parts[2])

        row = get_user(user.id)
        bal = row[3] if row else 0
        if amount > bal:
            await update.message.reply_text(
                f"❌ ব্যালেন্স কম। বর্তমান: ৳{bal:.2f}",
                reply_markup=main_menu()
            )
            return

        save_withdrawal(user.id, user.username, amount, method, number)

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💸 **নতুন উইথড্র**\n\n"
                 f"👤 {user.full_name}\n"
                 f"🔗 @{user.username or 'N/A'}\n"
                 f"📱 `{user.id}`\n"
                 f"📌 {method}\n"
                 f"📞 {number}\n"
                 f"💰 ৳{amount:.2f}",
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            "✅ উইথড্র রিকোয়েস্ট পাঠানো হয়েছে।",
            reply_markup=main_menu()
        )
    except:
        await update.message.reply_text(
            "❌ ফরম্যাট ভুল। আবার লিখুন:\n`বিকাশ, 01712345678, 500`",
            parse_mode="Markdown",
            reply_markup=back_kb()
        )


# ═══════════════════════════════════════
#  ℹ️ সাপোর্ট
# ═══════════════════════════════════════
async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ **সাপোর্ট**\n\nআপনার সমস্যা লিখুন।",
        parse_mode="Markdown",
        reply_markup=back_kb()
    )


async def support_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if text == "🔙 মেইন মেনু":
        await update.message.reply_text("মেইন মেনু", reply_markup=main_menu())
        return

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 **সাপোর্ট**\n\n"
             f"👤 {user.full_name}\n"
             f"🔗 @{user.username or 'N/A'}\n"
             f"📱 `{user.id}`\n\n"
             f"💬 {text}",
        parse_mode="Markdown"
    )
    await update.message.reply_text("✅ পাঠানো হয়েছে।", reply_markup=main_menu())


# ═══════════════════════════════════════
#  Notification Worker
# ═══════════════════════════════════════
async def notification_worker(context: ContextTypes.DEFAULT_TYPE):
    try:
        pending = get_pending_notifications(limit=20)
        for notif_id, user_id, message in pending:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown"
                )
                mark_notification_sent(notif_id)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"Notify {user_id} failed: {e}")
                mark_notification_sent(notif_id)
    except Exception as e:
        logger.error(f"Worker error: {e}")


# ═══════════════════════════════════════
#  BUILD USER APP
# ═══════════════════════════════════════
def build_user_app():
    """User Bot Application বানায় (main.py থেকে কল হবে)"""
    app = ApplicationBuilder().token(USER_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📊 ফাইল সাবমিট$"), file_submit))
    app.add_handler(MessageHandler(filters.Regex("^💵 ব্যালেন্স$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^📋 আমার রিপোর্ট$"), my_report))
    app.add_handler(MessageHandler(filters.Regex("^💸 উইথড্র$"), withdraw_start))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ সাপোর্ট$"), support_start))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.add_handler(CallbackQueryHandler(user_cat_click, pattern="^ucat_"))
    app.add_handler(CallbackQueryHandler(user_sub_click, pattern="^usub_"))
    app.add_handler(CallbackQueryHandler(user_cancel, pattern="^ucancel$"))
    app.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))

    # Withdraw & Support text handler (শেষে রাখতে হবে)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🔙 মেইন মেনু$"),
        support_handle
    ))

    # Notification worker — প্রতি ৩ সেকেন্ডে
    app.job_queue.run_repeating(notification_worker, interval=3, first=5)

    return app


# Local testing
if __name__ == "__main__":
    init_db()
    app = build_user_app()
    logger.info("👤 User Bot চালু...")
    app.run_polling(drop_pending_updates=True)
