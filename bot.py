import logging
import os
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

TOKEN = '8756382152:AAEQMXkOZflCB7RkgYt3Cp2oZyE3K0T5bJ4'

# Configurações do yt-dlp para extrair apenas o áudio em MP3
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': '%(title)s.%(ext)s', # Nome do arquivo será o título do vídeo
}

async def baixar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" in url or "youtu.be" in url:
        msg_espera = await update.message.reply_text("Processando o link... Aguarde.")
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
            
            # Envia o arquivo para o usuário
            await update.message.reply_audio(audio=open(filename, 'rb'))
            await msg_espera.delete()
            
            # Limpa o arquivo do seu PC após enviar
            os.remove(filename)
            
        except Exception as e:
            await update.message.reply_text(f"Erro ao baixar: {e}")
    else:
        await update.message.reply_text("Por favor, envie um link válido do YouTube.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), baixar_audio))
    
    print("Bot de música rodando...")
    application.run_polling()