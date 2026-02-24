import os
import logging
import httpx
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Configuração do yt-dlp (Manteve a qualidade alta)
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
}

async def baixar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" in url or "youtu.be" in url:
        msg_espera = await update.message.reply_text("⏳ Desviando do bloqueio do YouTube... Lendo o link.")
        
        try:
            # 1. Pega apenas o NOME do vídeo usando a API oficial do YouTube (Isso não dá bloqueio!)
            api_oembed = f"https://www.youtube.com/oembed?url={url}&format=json"
            async with httpx.AsyncClient() as client:
                resposta = await client.get(api_oembed)
                if resposta.status_code != 200:
                    await msg_espera.edit_text("❌ O link é privado ou inválido.")
                    return
                titulo_video = resposta.json().get("title")
            
            logging.info(f"Título descoberto: {titulo_video}")
            await msg_espera.edit_text(f"🎵 Achei a música: '{titulo_video}'\nBaixando da base de áudio alternativa (SoundCloud)...")

            # 2. Usa o yt-dlp para pesquisar ESSE NOME no SoundCloud e baixar o primeiro resultado
            busca_soundcloud = f"scsearch1:{titulo_video}"
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(busca_soundcloud, download=True)
                
                # Ajusta como o yt-dlp lê o arquivo dependendo de como o SoundCloud devolve a lista
                if 'entries' in info and len(info['entries']) > 0:
                    info_musica = info['entries'][0]
                else:
                    info_musica = info
                    
                filename = ydl.prepare_filename(info_musica).rsplit('.', 1)[0] + ".mp3"
            
            # 3. Envia o arquivo MP3 final para você no Telegram
            await update.message.reply_audio(audio=open(filename, 'rb'), title=titulo_video)
            await msg_espera.delete()
            
            # Limpa o arquivo do servidor do Render
            if os.path.exists(filename):
                os.remove(filename)
                
        except Exception as e:
            logging.error(f"Erro no Plano E: {e}")
            await update.message.reply_text(f"❌ O Truque do Espelho não encontrou a música: {str(e)}")
            
    else:
        await update.message.reply_text("Pode mandar o link do YouTube! 🎵")

if __name__ == '__main__':
    if not TOKEN:
        print("ERRO: Variável TELEGRAM_TOKEN não encontrada!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), baixar_audio))
        print("Bot iniciado com o Plano E (SoundCloud Mirror)!")
        application.run_polling()
