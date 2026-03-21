import os
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = "8395647369:AAGiAX64BeLIRM79LF9QLCWRw-VnRCsk5gE"
MAX_SIZE_MB = 50


def get_video_url(youtube_url):
    api_url = "https://9xbuddy.app/process"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://9xbuddy.app",
        "Referer": "https://9xbuddy.app/",
    }
    resp = requests.get(
        api_url,
        params={"url": youtube_url},
        headers=headers,
        timeout=30
    )
    data = resp.json()

    formats = data.get("formats", [])
    for fmt in formats:
        if fmt.get("ext") == "mp4" and fmt.get("url"):
            return fmt["url"]

    if formats and formats[0].get("url"):
        return formats[0]["url"]

    raise Exception("Video URL topilmadi")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! YouTube havolasini yuboring, video yuklab beraman.")


async def handle_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Iltimos, YouTube havolasini yuboring.")
        return

    msg = await update.message.reply_text("⏳ Video yuklanmoqda, kuting...")
    output_path = f"video_{update.message.chat_id}.mp4"

    try:
        video_url = get_video_url(url)
        r = requests.get(video_url, stream=True, timeout=60, headers={
            "User-Agent": "Mozilla/5.0"
        })
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        if size_mb > MAX_SIZE_MB:
            await msg.edit_text(f"❌ Video juda katta ({size_mb:.1f} MB). Maksimum {MAX_SIZE_MB} MB.")
            return

        await msg.edit_text("📤 Yuborilmoqda...")
        with open(output_path, "rb") as f:
            await update.message.reply_video(video=f, supports_streaming=True)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Xatolik: {str(e)[:200]}")
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


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
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
