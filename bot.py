import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8395647369:AAGiAX64BeLIRM79LF9QLCWRw-VnRCsk5gE"
MAX_SIZE_MB = 50

async def download_and_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("Menga Video Silkasini yuboring (TikTok, YouTube, Instagram...)")
        return

    msg = await update.message.reply_text("Videoni yuklayabman 📩")

    output_path = f"video_{update.message.chat_id}.mp4"

    ydl_opts = {
    "outtmpl": output_path,
    "format": "bestvideo+bestaudio/best/bestvideo/best",
    "merge_output_format": "mp4",
    "quiet": True,
    "no_warnings": True,
}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        if size_mb > MAX_SIZE_MB:
            await msg.edit_text(f"❌ Video slishkom bolshoe ({size_mb:.1f} MB). Maksimum {MAX_SIZE_MB} MB.")
            os.remove(output_path)
            return

        await msg.edit_text("📨 Yuborlayman...")
        with open(output_path, "rb") as video_file:
            await update.message.reply_video(video=video_file, supports_streaming=True)
        await msg.delete()

    except yt_dlp.utils.DownloadError as e:
        await msg.edit_text(f"❌ Ne udalos skachat video.\n{str(e)[:200]}")
    except Exception as e:
        await msg.edit_text(f"❌ Oshibka: {str(e)[:200]}")
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
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))
    print("Bot zapushchen...")
    app.run_polling()


if __name__ == "__main__":
    main()
