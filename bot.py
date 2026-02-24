import os
import shutil
import logging
import asyncio
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# O Render vai injetar o Token aqui automaticamente
TOKEN = os.environ.get('TELEGRAM_TOKEN')

# TRUQUE DO COOKIE: Copia da pasta bloqueada para a pasta livre
cookie_secreto = '/etc/secrets/cookies.txt'
cookie_livre = '/tmp/cookies.txt'

if os.path.exists(cookie_secreto):
    shutil.copyfile(cookie_secreto, cookie_livre)
    logging.info("Cookies copiados com sucesso para a pasta temporária!")

# Configurações do motor de download para Linux/Render
# Configurações do motor de download para Linux/Render
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'ffmpeg_location': './ffmpeg',
    'outtmpl': '/tmp/%(title)s.%(ext)s',
    'noplaylist': True,
    # O TRUQUE MÁGICO: Disfarça o bot de um celular Android para pular o bloqueio
    'extractor_args': {'youtube': {'client': ['android']}}, 
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
        print("Bot iniciado no Render com suporte a Cookies!")
        application.run_polling()

