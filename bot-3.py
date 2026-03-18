import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from scanner import scan_token
import re

# CONFIG
BOT_TOKEN = "8188108100:AAHjCDg51462ajyfdENjCYkoVvotsEI6QJc"
CHANNEL_USERNAME = "@SkullScannerOfficial"
CHANNEL_ID = "@SkullScannerOfficial"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple HTTP server biar Leapcell happy (port 8080)
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Skull Scanner is running!")
    def log_message(self, format, *args):
        pass  # suppress HTTP logs

def run_http_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()

# Check if user is member of channel
async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if not await is_member(context.bot, user_id):
        keyboard = [
            [InlineKeyboardButton("💀 Join Channel", url=f"https://t.me/SkullScannerOfficial")],
            [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="check_member")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"⛔ *AKSES DITOLAK!*\n\n"
            f"Hei *{user_name}*, untuk menggunakan *Skull Scanner* kamu harus:\n\n"
            f"1️⃣ Join channel kami dulu\n\n"
            f"Setelah join, klik tombol *✅ Saya Sudah Join* di bawah!",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return

    await update.message.reply_text(
        f"💀 *Selamat datang di Skull Scanner!*\n\n"
        f"Hei *{user_name}*! Bot ini akan scan token Solana secara lengkap.\n\n"
        f"📌 *Cara pakai:*\n"
        f"Tinggal kirim *Contract Address (CA)* Solana ke sini!\n\n"
        f"🔍 Bot akan langsung scan dan tampilkan info lengkap token!",
        parse_mode="Markdown"
    )

# Callback check member
async def check_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    await query.answer()

    if await is_member(context.bot, user_id):
        await query.edit_message_text(
            f"✅ *Verifikasi berhasil!*\n\n"
            f"Hei *{user_name}*! Selamat datang di *Skull Scanner* 💀\n\n"
            f"📌 *Cara pakai:*\n"
            f"Tinggal kirim *Contract Address (CA)* Solana ke sini!",
            parse_mode="Markdown"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("💀 Join Channel", url=f"https://t.me/SkullScannerOfficial")],
            [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="check_member")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"❌ *Kamu belum join channel!*\n\nJoin dulu ya bro, baru bisa pakai bot ini! 👇",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# Handle refresh button
async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer("🔄 Refreshing data...")

    if not await is_member(context.bot, user_id):
        await query.edit_message_text("⛔ Join channel dulu ya bro!")
        return

    ca = query.data.replace("refresh_", "")
    await query.edit_message_text("⏳ *Scanning...*", parse_mode="Markdown")
    
    result, keyboard = await scan_token(ca)
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)

# Handle CA message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not await is_member(context.bot, user_id):
        keyboard = [
            [InlineKeyboardButton("💀 Join Channel", url=f"https://t.me/SkullScannerOfficial")],
            [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="check_member")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⛔ *Join channel dulu ya bro!*",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return

    # Validate Solana CA (32-44 chars, base58)
    if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', text):
        await update.message.reply_text(
            "❌ *Format salah!*\n\nKirim Contract Address Solana yang valid ya bro!",
            parse_mode="Markdown"
        )
        return

    msg = await update.message.reply_text("💀 *Scanning token...*", parse_mode="Markdown")
    
    result, keyboard = await scan_token(text)
    await msg.edit_text(result, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)

def main():
    # Jalanin HTTP server di thread terpisah
    t = threading.Thread(target=run_http_server, daemon=True)
    t.start()
    logger.info("✅ HTTP server running on port 8080")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_member_callback, pattern="^check_member$"))
    app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("💀 Skull Scanner Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
