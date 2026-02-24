import os
import logging
import asyncio
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configuração de Logs para você ver o que acontece no painel do Render
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# O Render vai injetar o Token aqui automaticamente
TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Configurações do motor de download para Linux/Render
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'ffmpeg_location': './ffmpeg',        # <--- O SEGREDO ESTÁ AQUI (FFmpeg portátil)
    'outtmpl': '/tmp/%(title)s.%(ext)s',  # Pasta temporária do Linux
    'noplaylist': True,
    'cookiefile': '/etc/secrets/cookies.txt',
}

async def baixar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" in url or "youtu.be" in url:
        msg_espera = await update.message.reply_text("⏳ Processando áudio... Aguarde.")
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # Ajusta o nome do arquivo final
                filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"
            
            # Envia o arquivo MP3
            await update.message.reply_audio(audio=open(filename, 'rb'), title=info.get('title'))
            await msg_espera.delete()
            
            # Deleta o arquivo para não encher o servidor
            if os.path.exists(filename):
                os.remove(filename)
                
        except Exception as e:
            logging.error(f"Erro: {e}")
            await update.message.reply_text(f"❌ Erro ao processar: {str(e)}")
    else:
        await update.message.reply_text("Pode mandar o link do YouTube! 🎵")

if __name__ == '__main__':
    if not TOKEN:
        print("ERRO: Variável TELEGRAM_TOKEN não encontrada!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), baixar_audio))
        print("Bot iniciado no Render...")
        application.run_polling()

