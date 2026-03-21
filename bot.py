import os
import threading
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
import yt_dlp
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = "8395647369:AAGiAX64BeLIRM79LF9QLCWRw-VnRCsk5gE"
MAX_SIZE_MB = 50

CHOOSING, WAITING_LINK = range(2)

keyboard = [
    ["Instagram", "TikTok"],
    ["YouTube Shorts", "Pinterest"],
    ["Facebook", "Boshqalar"]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

PLATFORMS = {
    "Instagram": "instagram.com",
    "TikTok": "tiktok.com",
    "YouTube Shorts": "youtube.com",
    "Pinterest": "pinterest.com",
    "Facebook": "facebook.com",
    "Boshqalar": None,
}


def get_cookies_file():
    path = "/opt/render/project/src/www.youtube.com_cookies.txt"
    if os.path.exists(path):
        return path
    return None


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Qaysi platformadan video yuklashni xohlaysiz?",
        reply_markup=markup
    )
    return CHOOSING


async def platform_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice not in PLATFORMS:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.", reply_markup=markup)
        return CHOOSING
    ctx.user_data["platform"] = choice
    await update.message.reply_text(
        f"{choice} havolasini yuboring:",
        reply_markup=ReplyKeyboardRemove()
    )
    return WAITING_LINK


def get_ydl_opts(output_path, platform):
    base_opts = {
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        },
    }

    if platform == "YouTube Shorts":
        base_opts["format"] = "18"
        base_opts["extractor_args"] = {
            "youtube": {"player_client": ["android_vr"]}
        }
        cookies_file = get_cookies_file()
        if cookies_file:
            base_opts["cookiefile"] = cookies_file
    elif platform == "Pinterest":
        base_opts["format"] = "bestvideo+bestaudio/best/mp4"
        base_opts["postprocessors"] = [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }]
    elif platform == "Instagram":
        base_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        base_opts["extractor_args"] = {
            "instagram": {"include_dash_manifest": ["0"]}
        }
    elif platform == "Facebook":
        base_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    else:
        base_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"

    return base_opts


async def receive_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    platform = ctx.user_data.get("platform", "Boshqalar")

    if not url.startswith("http"):
        await update.message.reply_text("Iltimos, to'g'ri havola yuboring.")
        return WAITING_LINK

    msg = await update.message.reply_text("⏳ Video yuklanmoqda, kuting...")
    output_path = f"video_{update.message.chat_id}.mp4"
    cookies_file = None

    try:
        ydl_opts = get_ydl_opts(output_path, platform)
        cookies_file = ydl_opts.get("cookiefile")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        if size_mb > MAX_SIZE_MB:
            await msg.edit_text(f"❌ Video juda katta ({size_mb:.1f} MB). Maksimum {MAX_SIZE_MB} MB.")
            await update.message.reply_text("Platformani tanlang:", reply_markup=markup)
            return CHOOSING

        await msg.edit_text("📤 Yuborilmoqda...")
        with open(output_path, "rb") as f:
            await update.message.reply_video(video=f, supports_streaming=True)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Xatolik: {str(e)[:200]}")
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)

    await update.message.reply_text("Yana video yuklash uchun platformani tanlang:", reply_markup=markup)
    return CHOOSING


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, platform_chosen)],
            WAITING_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
