import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from scanner import scan_token
import re

BOT_TOKEN = os.getenv("BOT_TOKEN", "8188108100:AAHsjYQSYFz-Cn2Upk2-9n-5xGiX4h_H5Fw")
CHANNEL_ID = "@SkullScannerOfficial"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    if not await is_member(context.bot, user_id):
        keyboard = [
            [InlineKeyboardButton("💀 Join Channel", url="https://t.me/SkullScannerOfficial")],
            [InlineKeyboardButton("✅ I Already Joined", callback_data="check_member")]
        ]
        await update.message.reply_text(
            f"⛔ *ACCESS DENIED!*\n\nHey *{user_name}*, to use *Skull Scanner* you must:\n\n1️⃣ Join our channel first\n\nAfter joining, click *✅ I Already Joined* below!",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    await update.message.reply_text(
        f"💀 *Welcome to Skull Scanner!*\n\nHey *{user_name}*! This bot will scan Solana tokens in detail.\n\n📌 *How to use:*\nJust send a Solana *Contract Address (CA)* here!\n\nExample:\n`Dnb9dLSXxAarXVexehzeH8W8nFmLMNJSuGoaddZSwtog`\n\n🔍 The bot will instantly scan and display full token info!",
        parse_mode="Markdown")

async def check_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    await query.answer()
    if await is_member(context.bot, user_id):
        await query.edit_message_text(
            f"✅ *Verification successful!*\n\nHey *{user_name}*! Welcome to *Skull Scanner* 💀\n\n📌 *How to use:*\nJust send a Solana *Contract Address (CA)* here!\n\nExample:\n`Dnb9dLSXxAarXVexehzeH8W8nFmLMNJSuGoaddZSwtog`",
            parse_mode="Markdown")
    else:
        keyboard = [
            [InlineKeyboardButton("💀 Join Channel", url="https://t.me/SkullScannerOfficial")],
            [InlineKeyboardButton("✅ I Already Joined", callback_data="check_member")]
        ]
        await query.edit_message_text(
            "❌ *You haven't joined the channel yet!*\n\nPlease join first to use this bot! 👇",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer("🔄 Refreshing data...")
    if not await is_member(context.bot, user_id):
        await query.edit_message_text("⛔ Please join our channel first!")
        return
    ca = query.data.replace("refresh_", "")
    await query.edit_message_text("⏳ *Scanning...*", parse_mode="Markdown")
    result, keyboard = await scan_token(ca)
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not await is_member(context.bot, user_id):
        keyboard = [
            [InlineKeyboardButton("💀 Join Channel", url="https://t.me/SkullScannerOfficial")],
            [InlineKeyboardButton("✅ I Already Joined", callback_data="check_member")]
        ]
        await update.message.reply_text(
            "⛔ *Please join our channel first!*",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', text):
        await update.message.reply_text(
            "❌ *Invalid format!*\n\nPlease send a valid Solana Contract Address!\n\nExample:\n`Dnb9dLSXxAarXVexehzeH8W8nFmLMNJSuGoaddZSwtog`",
            parse_mode="Markdown")
        return
    msg = await update.message.reply_text("💀 *Scanning token...*", parse_mode="Markdown")
    result, keyboard = await scan_token(text)
    await msg.edit_text(result, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_member_callback, pattern="^check_member$"))
    app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("💀 Skull Scanner Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
