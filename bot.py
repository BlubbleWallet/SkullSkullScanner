import logging
import asyncio
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from scanner import scan_token
import re

BOT_TOKEN = "8188108100:AAHjCDg51462ajyfdENjCYkoVvotsEI6QJc"
CHANNEL_ID = "@SkullScannerOfficial"
WEBHOOK_URL = "https://kullkullscanner-blubblewallet8131-o1n60wfs.leapcell.dev"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = None
loop = None

async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    if not await is_member(context.bot, user_id):
        kb = [[InlineKeyboardButton("💀 Join Channel", url="https://t.me/SkullScannerOfficial")],
              [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="check_member")]]
        await update.message.reply_text(
            f"⛔ *AKSES DITOLAK!*\n\nHei *{user_name}*, join channel kami dulu!\nSetelah join, klik *✅ Saya Sudah Join*",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return
    await update.message.reply_text(
        f"💀 *Selamat datang di Skull Scanner!*\n\nHei *{user_name}*! Kirim CA Solana ke sini untuk scan token!\n\n🔍 Bot akan tampilkan info lengkap token!",
        parse_mode="Markdown")

async def check_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_member(context.bot, query.from_user.id):
        await query.edit_message_text(
            f"✅ *Verifikasi berhasil!*\n\nHei *{query.from_user.first_name}*! Selamat datang 💀\n\nKirim CA Solana ke sini!",
            parse_mode="Markdown")
    else:
        kb = [[InlineKeyboardButton("💀 Join Channel", url="https://t.me/SkullScannerOfficial")],
              [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="check_member")]]
        await query.edit_message_text("❌ *Belum join!*\n\nJoin dulu ya bro! 👇",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 Refreshing...")
    if not await is_member(context.bot, query.from_user.id):
        await query.edit_message_text("⛔ Join channel dulu!")
        return
    ca = query.data.replace("refresh_", "")
    await query.edit_message_text("⏳ *Scanning...*", parse_mode="Markdown")
    result, kb = await scan_token(ca)
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not await is_member(context.bot, user_id):
        kb = [[InlineKeyboardButton("💀 Join Channel", url="https://t.me/SkullScannerOfficial")],
              [InlineKeyboardButton("✅ Saya Sudah Join", callback_data="check_member")]]
        await update.message.reply_text("⛔ *Join channel dulu ya bro!*",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return
    if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', text):
        await update.message.reply_text("❌ *Format salah!*\n\nKirim Contract Address Solana yang valid!", parse_mode="Markdown")
        return
    msg = await update.message.reply_text("💀 *Scanning token...*", parse_mode="Markdown")
    result, kb = await scan_token(text)
    await msg.edit_text(result, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True)

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Skull Scanner OK")

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        try:
            data = json.loads(body.decode('utf-8'))
            update = Update.de_json(data, app.bot)
            asyncio.run_coroutine_threadsafe(app.process_update(update), loop)
        except Exception as e:
            logger.error(f"Webhook error: {e}")

    def log_message(self, format, *args):
        pass

async def setup():
    global app
    app = Application.builder().token(BOT_TOKEN).updater(None).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_member_callback, pattern="^check_member$"))
    app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.initialize()
    await app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    await app.start()
    logger.info("✅ Webhook set!")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup())
    server = HTTPServer(("0.0.0.0", 8080), WebhookHandler)
    logger.info("✅ HTTP server on port 8080")
    server.serve_forever()
