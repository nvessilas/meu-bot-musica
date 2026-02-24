import os
import logging
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Configuração base (sem os disfarces ainda)
base_ydl_opts = {
    'format': 'm4a/bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'ffmpeg_location': './ffmpeg',
    'outtmpl': '/tmp/%(title)s.%(ext)s',
    'noplaylist': True,
}

# A SUA IDEIA AQUI: Nossa lista de métodos/disfarces para tentar um por um
estrategias = [
    {'youtube': {'client': ['android_vr']}},  # Tentativa 1: Óculos VR
    {'youtube': {'client': ['tv']}},          # Tentativa 2: Smart TV
    {'youtube': {'client': ['android']}},     # Tentativa 3: Celular Android
    {'youtube': {'client': ['ios']}},         # Tentativa 4: iPhone
    {'youtube': {'client': ['web']}},         # Tentativa 5: PC Normal
]

async def baixar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" in url or "youtu.be" in url:
        msg_espera = await update.message.reply_text("⏳ Aplicando vários métodos para baixar... Aguarde.")
        
        sucesso = False
        
        # O bot vai testar cada método da nossa lista
        for i, estrategia in enumerate(estrategias):
            try:
                logging.info(f"Tentando método {i+1}...")
                
                # Junta a configuração base com o método atual da lista
                opts_atuais = base_ydl_opts.copy()
                opts_atuais['extractor_args'] = estrategia
                
                with YoutubeDL(opts_atuais) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"
                
                # Se chegou nesta linha, significa que O DOWNLOAD FUNCIONOU!
                await update.message.reply_audio(audio=open(filename, 'rb'), title=info.get('title'))
                
                # Limpa o arquivo
                if os.path.exists(filename):
                    os.remove(filename)
                    
                sucesso = True
                break  # O comando "break" faz o bot parar de tentar, pois já deu certo!
                
            except Exception as e:
                # Se deu erro, ele apenas avisa no log secreto do Render e vai para a próxima tentativa
                logging.warning(f"Método {i+1} bloqueado pelo YouTube. Tentando o próximo...")
                continue
        
        await msg_espera.delete()
        
        # Se esgotou todas as tentativas e nenhum funcionou
        if not sucesso:
            await update.message.reply_text("❌ O YouTube bloqueou absolutamente todos os nossos métodos hoje. Tente outro link!")
            
    else:
        await update.message.reply_text("Pode mandar o link do YouTube! 🎵")

if __name__ == '__main__':
    if not TOKEN:
        print("ERRO: Variável TELEGRAM_TOKEN não encontrada!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), baixar_audio))
        print("Bot iniciado com Estratégia de Múltiplas Tentativas!")
        application.run_polling()
