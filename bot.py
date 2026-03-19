import os
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8395647369:AAE_ZLO7BnwhJthA-aYDTZwrFujYpi7j4uM"  # Poluchi u @BotFather
MAX_SIZE_MB = 50  # Telegram limit dlya botov — 50 MB

async def download_and_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # Proverka — ssylka li eto
    if not url.startswith("http"):
        await update.message.reply_text("Otprav mne ssylku na video (TikTok, YouTube, Instagram...)")
        return

    msg = await update.message.reply_text("⏳ Skachivayu video, podozhi...")

    output_path = f"video_{update.message.chat_id}.mp4"

    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestvideo[ext=mp4][filesize<50M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<50M]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Proverka razmera fayla
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        if size_mb > MAX_SIZE_MB:
            await msg.edit_text(f"❌ Video slishkom bolshoe ({size_mb:.1f} MB). Maksimum {MAX_SIZE_MB} MB.")
            os.remove(output_path)
            return

        await msg.edit_text("📤 Otpravlyayu...")
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


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))
    print("Bot zapushchen...")
    app.run_polling()


if __name__ == "__main__":
    main()