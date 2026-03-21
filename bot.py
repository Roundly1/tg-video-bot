import os
import threading
import requests
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

COBALT_API = "https://cobalt.tools/api/json"
COBALT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Qaysi platformadan video yuklashni xohlaysiz?",
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


def download_via_cobalt(url, output_path):
    resp = requests.post(
        COBALT_API,
        headers=COBALT_HEADERS,
        json={"url": url, "vQuality": "720", "filenamePattern": "basic"},
        timeout=30
    )
    data = resp.json()
    status = data.get("status")

    if status == "stream" or status == "redirect":
        video_url = data.get("url")
        r = requests.get(video_url, stream=True, timeout=60)
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    elif status == "picker":
        video_url = data["picker"][0]["url"]
        r = requests.get(video_url, stream=True, timeout=60)
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    else:
        raise Exception(f"Cobalt xatolik: {data.get('text', str(data))}")


def get_ydl_opts(output_path, platform):
    base_opts = {
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
    }

    if platform == "Pinterest":
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
        await update.message.reply_text("Iltimos, to'g'ri havola yuboring (http... bilan boshlanishi kerak)")
        return WAITING_LINK

    msg = await update.message.reply_text("⏳ Video yuklanmoqda, kuting...")
    output_path = f"video_{update.message.chat_id}.mp4"

    try:
        if platform == "YouTube Shorts":
            download_via_cobalt(url, output_path)
        else:
            ydl_opts = get_ydl_opts(output_path, platform)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        if size_mb > MAX_SIZE_MB:
            await msg.edit_text(f"❌ Video juda katta ({size_mb:.1f} MB). Maksimum {MAX_SIZE_MB} MB.")
            os.remove(output_path)
            await update.message.reply_text("Boshqa video yuborish uchun platformani tanlang:", reply_markup=markup)
            return CHOOSING

        await msg.edit_text("📤 Yuborilmoqda...")
        with open(output_path, "rb") as video_file:
            await update.message.reply_video(video=video_file, supports_streaming=True)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Xatolik: {str(e)[:200]}")
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

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
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("boshlash", start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, platform_chosen)],
            WAITING_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
        },
        fallbacks=[CommandHandler("boshlash", start)],
    )

    app.add_handler(conv_handler)
    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
