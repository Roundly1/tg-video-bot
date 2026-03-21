import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = "8395647369:AAGiAX64BeLIRM79LF9QLCWRw-VnRCsk5gE"
MAX_SIZE_MB = 50


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! YouTube havolasini yuboring, video yuklab beraman.")


async def handle_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Iltimos, YouTube havolasini yuboring.")
        return

    msg = await update.message.reply_text("⏳ Video yuklanmoqda, kuting...")
    output_path = f"video_{update.message.chat_id}.mp4"

    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best/18",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr"]
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

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
